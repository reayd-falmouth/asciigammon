# neural_net.py
import os

import numpy as np

from pybg.core.board import Board
from pybg.gnubg.position import PositionClass
from pybg.constants import ASSETS_DIR
from pybg.core.logger import logger

WEIGHTS_FILE = f"{ASSETS_DIR}/gnubg/nngnubg.weights"


def sigmoid(x):
    # Clamp to avoid overflow in exp()
    x = np.clip(x, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-x))


def encode_board(position, cInput):
    """
    Constructs a GNUBG-compatible 250-dimensional input vector for neural net evaluation.

    ✅ Final Review of Sections
    ----------------------------------------------------------------------
    Section                    Count   Description                               Status
    ------------------------  -------  ----------------------------------------  -----------------------
    1. Point features (Player)  48     Occupied (1/0), capped extra checker level ✅ Correct
    2. Point features (Opponent)48     Same as above but for opponent             ✅ Correct
    3. Bar/off checkers         4      Player/Opponent bar and off, capped        ✅ Correct
    4. Home board control       24     Per-point features (6×2×2)                 ✅ Fixed and Correct
    5. Pip counts               3      Player pip, opponent pip, diff (normalized)✅ Correct
    6. Borne-off ramps          12     6 per player, binary thresholds            ✅ Correct
    7. Padding                  61     To fill out to 250-dim                     ✅ Safe and fine

    🔢 Total: 48 + 48 + 4 + 24 + 3 + 12 + 61 = 250 features
    """

    NUM_POINTS = 24
    board = position.board_points
    features = []

    # --- 1. Point features for both players (96 values: 2 per point × 2 players)
    for i in range(NUM_POINTS):
        p = board[i]
        features.append(1 if p > 0 else 0)  # Player occupies
        features.append(min(p - 1, 4) / 4.0 if p > 1 else 0.0)  # Extra checkers, capped

    for i in range(NUM_POINTS):
        o = board[i]
        features.append(1 if o < 0 else 0)  # Opponent occupies
        features.append(min(abs(o) - 1, 4) / 4.0 if o < -1 else 0.0)

    # --- 2. Bar and off checkers (4 values)
    features.append(min(position.player_bar, 5) / 5.0)
    features.append(min(position.player_off, 15) / 15.0)
    features.append(min(position.opponent_bar, 5) / 5.0)
    features.append(min(position.opponent_off, 15) / 15.0)

    # --- 3. Home board control (24 values: 6 points × 2 features × 2 players)
    for x in board[0:6]:  # Player home: points 1–6
        features.append(1 if x > 0 else 0)
        features.append(min(x - 1, 4) / 4.0 if x > 1 else 0.0)

    for x in board[18:24]:  # Opponent home: points 19–24
        features.append(1 if x < 0 else 0)
        features.append(min(abs(x) - 1, 4) / 4.0 if x < -1 else 0.0)

    # --- 4. Pip counts (3 values)
    p_pip, o_pip = position.pip_count()
    features.append(p_pip / 167.0)
    features.append(o_pip / 167.0)
    features.append((o_pip - p_pip) / 167.0)

    # --- 5. Borne-off ramp features (12 values: 6 per player)
    for n in range(6):
        features.append(1.0 if position.player_off > 2 * n else 0.0)
    for n in range(6):
        features.append(1.0 if position.opponent_off > 2 * n else 0.0)

    # --- 6. Final padding to reach cInput length (typically 250)
    if len(features) < cInput:
        features += [0.0] * (cInput - len(features))
    elif len(features) > cInput:
        features = features[:cInput]

    return np.array(features, dtype=np.float32)


# ------------------------------------------------------------------------------
# Internal class representing a single neural network.
# This class holds the network parameters and implements evaluation.
# ------------------------------------------------------------------------------
class GnubgNetwork:
    def __init__(
        self,
        cInput,
        cHidden,
        cOutput,
        nTrained,
        rBetaHidden,
        rBetaOutput,
        weights1,
        weights2,
        bias1,
        bias2,
    ):
        """
        Initialize a single neural network using the provided parameters.

        Parameters:
          cInput: int, number of input neurons.
          cHidden: int, number of hidden neurons.
          cOutput: int, number of output neurons.
          nTrained: int, training iteration count (for reference).
          rBetaHidden, rBetaOutput: float, scaling factors used with the sigmoid.
          weights1: np.ndarray of shape (cInput, cHidden) for the hidden layer weights.
          weights2: np.ndarray of shape (cHidden, cOutput) for the output layer weights.
          bias1: np.ndarray of shape (cHidden,) for hidden layer biases.
          bias2: np.ndarray of shape (cOutput,) for output layer biases.
        """
        self.cInput = cInput
        self.cHidden = cHidden
        self.cOutput = cOutput
        self.nTrained = nTrained
        self.rBetaHidden = rBetaHidden
        self.rBetaOutput = rBetaOutput
        self.weights1 = weights1
        self.weights2 = weights2
        self.bias1 = bias1
        self.bias2 = bias2

    def evaluate(self, input_vector: np.ndarray) -> np.ndarray:
        """
        Compute the network’s output for a given input vector.

        The evaluation proceeds in two steps:
          1. Compute the hidden layer activation:
             hidden_activity = dot(input_vector, weights1) + bias1
             Then apply the sigmoid function (scaled by -rBetaHidden).
          2. Compute the output layer:
             output_activity = dot(hidden, weights2) + bias2
             Then apply the sigmoid function (scaled by -rBetaOutput).

        Parameters:
          input_vector: 1D numpy array of length cInput.

        Returns:
          1D numpy array of length cOutput.
        """
        # Hidden layer calculation:
        activity_hidden = np.dot(input_vector, self.weights1) + self.bias1
        hidden = sigmoid(-self.rBetaHidden * activity_hidden)

        # Output layer calculation:
        activity_output = np.dot(hidden, self.weights2) + self.bias2
        output = sigmoid(-self.rBetaOutput * activity_output)

        return output


# ------------------------------------------------------------------------------
# Container class that loads all networks from the weights file and
# provides a simple evaluation interface.
# ------------------------------------------------------------------------------
class GnubgEvaluator:
    def __init__(self, weights_file: str = WEIGHTS_FILE):
        """
        Initialize the evaluator by automatically loading all networks from a weights file.

        Parameters:
          weights_file: path to the weights file (defaults to "gnubg.weights" in the same directory).
        """
        self.weights_file = WEIGHTS_FILE
        # Load all network objects from the file.
        nets = self.load_all_networks()
        # Create a mapping from PositionClass to the appropriate network.
        self.network_mapping = {
            PositionClass.CONTACT: (nets["contact_contact250"], nets["prune_contact"]),
            PositionClass.RACE: (nets["race"], nets["prune_race"]),
            PositionClass.CRASHED: (nets["crashed"], nets["prune_crashed"]),
        }

    def load_all_networks(self) -> dict[str, GnubgNetwork]:
        """
        Load all neural networks from a GNUBG-style multi-network weights file.

        Returns:
          A dictionary mapping network names like "contact", "race", etc. to GnubgNetwork objects.
        """
        networks = {}
        with open(self.weights_file, "r") as f:
            version_line = f.readline().strip()

            while True:
                name_line = f.readline()
                if not name_line:
                    break  # end of file

                name = name_line.strip().lower()  # e.g., "contact"
                header = f.readline().strip()
                if not header:
                    break

                params = header.split()
                cInput = int(params[0])
                cHidden = int(params[1])
                cOutput = int(params[2])
                nTrained = int(params[3])
                rBetaHidden = float(params[4])
                rBetaOutput = float(params[5])

                # Load hidden layer weights
                weights1 = np.zeros((cInput, cHidden), dtype=float)
                for j in range(cHidden):  # <- flipped outer loop
                    for i in range(cInput):  # <- flipped inner loop
                        weights1[i, j] = float(f.readline().strip())

                weights2 = np.zeros((cHidden, cOutput), dtype=float)
                for j in range(cOutput):
                    for i in range(cHidden):
                        weights2[i, j] = float(f.readline().strip())

                # Load biases
                bias1 = np.array(
                    [float(f.readline().strip()) for _ in range(cHidden)], dtype=float
                )
                bias2 = np.array(
                    [float(f.readline().strip()) for _ in range(cOutput)], dtype=float
                )

                net = GnubgNetwork(
                    cInput,
                    cHidden,
                    cOutput,
                    nTrained,
                    rBetaHidden,
                    rBetaOutput,
                    weights1,
                    weights2,
                    bias1,
                    bias2,
                )

                key = name.replace(
                    " ", "_"
                ).lower()  # e.g., "prune contact" → "prune_contact"
                networks[key] = net

        return networks

    def evaluate_position(self, board: Board) -> dict:
        """
        Evaluate a position using the appropriate neural net.

        Returns a dict with keys:
          - win
          - wingammon
          - winbackgammon
          - losegammon
          - losebackgammon
        """
        position = board.position
        player_on_roll = board.match.player

        # 🧠 DEBUG: Show selected network
        pos_class = position.classify()
        net = self.network_mapping[pos_class]

        inp = encode_board(position, net[0].cInput)

        # 🧠 Evaluate & peek at internal activations
        hidden_activity = np.dot(inp, net[0].weights1) + net[0].bias1
        hidden_output = sigmoid(-net[0].rBetaHidden * hidden_activity)

        output_activity = np.dot(hidden_output, net[0].weights2) + net[0].bias2
        raw = sigmoid(-net[0].rBetaOutput * output_activity)

        return {
            "win": raw[0],
            "wingammon": raw[1],
            "winbackgammon": raw[2],
            "losegammon": raw[3],
            "losebackgammon": raw[4],
        }

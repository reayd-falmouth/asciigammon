import pygame

from pybg.constants import ASSETS_DIR
from pybg.core.logger import logger
from typing import Union


class SoundManager:
    """Handles game sound effects and background music."""

    def __init__(self):
        pygame.mixer.init()

        # Load sounds from assets directory
        self.move_sound = pygame.mixer.Sound(f"{ASSETS_DIR}/audio/move.wav")
        self.hit_sound = pygame.mixer.Sound(
            f"{ASSETS_DIR}/audio/drop.wav"
        )  # Drop = hit
        self.chequer_sound = pygame.mixer.Sound(f"{ASSETS_DIR}/audio/chequer.wav")
        self.roll_sound = pygame.mixer.Sound(f"{ASSETS_DIR}/audio/roll.wav")
        self.double_sound = pygame.mixer.Sound(f"{ASSETS_DIR}/audio/double.wav")
        self.take_sound = pygame.mixer.Sound(f"{ASSETS_DIR}/audio/take.wav")
        self.resign_sound = pygame.mixer.Sound(f"{ASSETS_DIR}/audio/resign.wav")
        self.matchover_sound = pygame.mixer.Sound(f"{ASSETS_DIR}/audio/matchover.wav")
        self.gameover_sound = pygame.mixer.Sound(f"{ASSETS_DIR}/audio/gameover.wav")
        self.fanfare_sound = pygame.mixer.Sound(f"{ASSETS_DIR}/audio/fanfare.wav")
        self.exit_sound = pygame.mixer.Sound(f"{ASSETS_DIR}/audio/haere-ra.wav")
        self.background_music = pygame.mixer.Sound(f"{ASSETS_DIR}/audio/dance.wav")

        # Optional: Set default volume levels
        self.move_sound.set_volume(1.0)
        self.hit_sound.set_volume(1.0)
        self.chequer_sound.set_volume(0.5)
        self.roll_sound.set_volume(1.0)
        self.double_sound.set_volume(1.0)
        self.take_sound.set_volume(1.0)
        self.resign_sound.set_volume(1.0)
        self.matchover_sound.set_volume(1.0)
        self.gameover_sound.set_volume(1.0)
        self.fanfare_sound.set_volume(1.0)
        self.exit_sound.set_volume(1.0)
        self.background_music.set_volume(0.2)

    # Sound playback methods
    def play_move(self):
        self.move_sound.play()

    def play_hit(self):
        self.hit_sound.play()

    def play_chequer(self):
        self.chequer_sound.play()

    def play_roll(self):
        self.roll_sound.play()

    def play_double(self):
        self.double_sound.play()

    def play_take(self):
        self.take_sound.play()

    def play_resign(self):
        self.resign_sound.play()

    def play_matchover(self):
        self.matchover_sound.play()

    def play_gameover(self):
        self.gameover_sound.play()

    def play_fanfare(self):
        self.fanfare_sound.play()

    def play_exit(self):
        self.exit_sound.play()

    def play_sound(self, action: Union[str, tuple]):
        """Plays a sound based on the action name."""
        logger.debug(f"Sound play requested for action {action}")
        if isinstance(action, tuple):
            action = action[0]

        sound_map = {
            "new": self.fanfare_sound,
            "roll": self.roll_sound,
            "move": self.move_sound,
            "double": self.double_sound,
            "take": self.take_sound,
            "drop": self.resign_sound,  # You might prefer a buzzer or alert sound
            "accept": self.chequer_sound,
            "reject": self.hit_sound,
            "resign": self.resign_sound,
        }

        sound = sound_map.get(action)
        if sound:
            logger.debug(f"Playing sound for {action}")
            sound.play()

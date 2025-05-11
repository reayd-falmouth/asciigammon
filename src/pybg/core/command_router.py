# pybg/core/command_router.py

import importlib
import pkgutil


class CommandRouter:
    def __init__(self, shell):
        self.shell = shell
        self.commands = {}  # fallback/default global commands
        self.module_commands = {}  # module_name -> command dict
        self.shortcuts = {}
        self.modules = []
        self.load_modules()

    def load_modules(self):
        import pybg.modules

        for _, modname, _ in pkgutil.iter_modules(pybg.modules.__path__):
            module = importlib.import_module(f"pybg.modules.{modname}")
            if hasattr(module, "register"):
                instance = module.register(self.shell)
                self.modules.append(instance)
                cmds, keys, help_entries = instance.register()

                category = getattr(instance, "category", "General").lower()

                # Register module-specific commands
                if category not in self.module_commands:
                    self.module_commands[category] = {}
                self.module_commands[category].update(cmds)

                # Also allow global fallback for non-conflicting commands
                for cmd_name, func in cmds.items():
                    if cmd_name not in self.commands:
                        self.commands[cmd_name] = func

                self.shortcuts.update(keys)

                for cmd, desc in help_entries.items():
                    self.shell.help.register(cmd, desc, category=category)

    def handle(self, input_string: str):
        args = input_string.strip().split()
        if not args:
            return "Empty command."

        cmd, *rest = args
        cmd = cmd.lower()

        # First try active module-specific command
        active_module = (self.shell.active_module or "").lower()
        if active_module and active_module in self.module_commands:
            module_cmds = self.module_commands[active_module]
            if cmd in module_cmds:
                return module_cmds[cmd](rest)

        # Fallback to global/default command set
        if cmd in self.commands:
            return self.commands[cmd](rest)

        return f"Unknown command: {cmd}"

from src.Gui import MainGUI
from src.Utils import setup_local_user_cfgs, validate_requirements

if __name__ == "__main__":
    validate_requirements()
    setup_local_user_cfgs()
    app = MainGUI()
    app.mainloop()
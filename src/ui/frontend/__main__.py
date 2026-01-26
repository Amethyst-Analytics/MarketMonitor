"""Package entrypoint so ``python -m ui.frontend`` runs the Streamlit app."""

import streamlit.web.cli as stcli

if __name__ == "__main__":
    stcli.main_run()

from flask import Flask
smeli_app = Flask(__name__)
from smeli_web import routes

VITE_MANIFEST_PATH = (
        Path(smeli_app.static_folder)
        / "dist"
        / ".vite"
        / "manifest.json"
)

with VITE_MANIFEST_PATH.open() as f:
    VITE_MANIFEST = json.load(f)


def vite_asset(entrypoint):
    entry = VITE_MANIFEST.get(entrypoint)

    if entry is None:
        raise RuntimeError(
            f"Vite entrypoint not found in manifest: {entrypoint}"
        )

    return f"/static/dist/{entry['file']}"


@smeli_app.context_processor
def inject_vite():
    return {
        "vite_asset": vite_asset
    }

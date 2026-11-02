"""Optional live Jev check on one marked JPEG. Requires Pillow and TYPESAFE_API_KEY."""

import argparse
import base64
import io
import json
import math
import os
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

CONTEXT = "Evaluate the specific marked item in this crop, using its surroundings for context."
QUESTION = (
    "Is the item framed by the magenta corner marks clearly a discarded manufactured object "
    "that a litter-picking robot should collect? A natural object, vegetation, an animal, "
    "something worn or in use, fixed infrastructure, bare ground, or an unclear target should be left alone."
)


def payload(path):
    from PIL import Image

    image_bytes = path.read_bytes()
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.format != "JPEG":
            raise ValueError("Expected a JPEG with the target marked in the image")
        w, h = image.size
        if min(w, h) < 280:
            factor = 280 / min(w, h)
            scaled = image.resize((math.ceil(w * factor), math.ceil(h * factor)), Image.Resampling.BICUBIC)
            encoded = io.BytesIO()
            scaled.save(encoded, "JPEG", quality=95)
            image_bytes = encoded.getvalue()
    key = str(uuid.uuid4())
    return {
        "model": "jev-1.14.0",
        "state": [CONTEXT, key],
        "assets": {key: {"type": "image", "format": "jpg", "data_base64": base64.b64encode(image_bytes).decode("ascii")}},
        "questions": {"pickup": {"type": "noul", "instructions": QUESTION}},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    token = os.environ.get("TYPESAFE_API_KEY")
    if not token:
        parser.error("Set TYPESAFE_API_KEY to make a live request")
    request = Request(
        "https://api.typesafe.ai/v1/systemone",
        data=json.dumps(payload(args.image)).encode(),
        headers={"Content-Type": "application/json", "TypeSafe-Danger-Zone-Images": "true",
                 "Authorization": f"Bearer {token}"},
    )
    with urlopen(request, timeout=32) as response:
        score = float(json.load(response)["answers"]["pickup"]["noul"])
    print(f"{score:.2f}  {'Pick up' if score >= .90 else 'Leave it'}")


if __name__ == "__main__":
    main()

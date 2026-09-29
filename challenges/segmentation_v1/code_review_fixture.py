from pathlib import Path

import numpy as np
import torch


def run_volume(model, volume_path, output_path, device="cuda"):
    volume = np.load(volume_path)
    model.to(device)

    prediction = np.zeros(volume.shape, dtype=np.uint8)
    tile = 128
    overlap = 32

    for z in range(0, volume.shape[0], tile - overlap):
        for y in range(0, volume.shape[1], tile - overlap):
            for x in range(0, volume.shape[2], tile - overlap):
                patch = volume[z : z + tile, y : y + tile, x : x + tile]
                tensor = torch.tensor(patch).float().unsqueeze(0).unsqueeze(0)
                logits = model(tensor.to(device))
                mask = torch.softmax(logits, dim=1).argmax(dim=1)
                prediction[z : z + tile, y : y + tile, x : x + tile] = mask.cpu().numpy()[0]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, prediction)
    print("finished", output_path)

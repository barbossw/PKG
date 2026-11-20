import math
import os
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from buffer_wrapper import BufferWrapper


class ImageAlgorithms:
    @staticmethod
    def _report(progress_callback, value: int):
        if progress_callback is not None:
            progress_callback(int(value))

    @staticmethod
    def add_brightness(buffer: BufferWrapper, value: float, progress_callback=None) -> BufferWrapper:
        ImageAlgorithms._report(progress_callback, 20)
        out = np.clip(buffer.data + float(value), 0.0, 255.0)
        ImageAlgorithms._report(progress_callback, 100)
        return BufferWrapper(out)

    @staticmethod
    def multiply_contrast(buffer: BufferWrapper, factor: float, progress_callback=None) -> BufferWrapper:
        ImageAlgorithms._report(progress_callback, 20)
        out = np.clip(buffer.data * float(factor), 0.0, 255.0)
        ImageAlgorithms._report(progress_callback, 100)
        return BufferWrapper(out)

    @staticmethod
    def negative(buffer: BufferWrapper, progress_callback=None) -> BufferWrapper:
        ImageAlgorithms._report(progress_callback, 20)
        out = 255.0 - np.clip(buffer.data, 0.0, 255.0)
        ImageAlgorithms._report(progress_callback, 100)
        return BufferWrapper(out)

    @staticmethod
    def gamma_correction(buffer: BufferWrapper, gamma: float, progress_callback=None) -> BufferWrapper:
        ImageAlgorithms._report(progress_callback, 20)
        g = max(0.01, float(gamma))
        norm = np.clip(buffer.data, 0.0, 255.0) / 255.0
        out = np.power(norm, g) * 255.0
        ImageAlgorithms._report(progress_callback, 100)
        return BufferWrapper(out)

    @staticmethod
    def log_transform(buffer: BufferWrapper, gain: float = 1.0, progress_callback=None) -> BufferWrapper:
        ImageAlgorithms._report(progress_callback, 20)
        clamped = np.clip(buffer.data, 0.0, 255.0)
        max_val = float(np.max(clamped))
        if max_val > 0.0:
            c = (255.0 / math.log1p(max_val)) * float(gain)
            out = np.clip(c * np.log1p(clamped), 0.0, 255.0)
        else:
            out = np.zeros_like(clamped)
        ImageAlgorithms._report(progress_callback, 100)
        return BufferWrapper(out)

    @staticmethod
    def linear_contrast(buffer: BufferWrapper, progress_callback=None) -> BufferWrapper:
        ImageAlgorithms._report(progress_callback, 15)
        out = np.zeros_like(buffer.data)
        if buffer.channels == 1:
            min_v = float(np.min(buffer.data))
            max_v = float(np.max(buffer.data))
            if max_v > min_v:
                out = (buffer.data - min_v) / (max_v - min_v) * 255.0
            else:
                out = buffer.data.copy()
        else:
            for c in range(buffer.channels):
                chan = buffer.data[:, :, c]
                min_v = float(np.min(chan))
                max_v = float(np.max(chan))
                if max_v > min_v:
                    out[:, :, c] = (chan - min_v) / (max_v - min_v) * 255.0
                else:
                    out[:, :, c] = chan
                ImageAlgorithms._report(progress_callback, 15 + int((c + 1) * 85 / buffer.channels))
        ImageAlgorithms._report(progress_callback, 100)
        return BufferWrapper(out)

    @staticmethod
    def _equalize_channel_u8(channel_u8: np.ndarray) -> np.ndarray:
        hist = np.bincount(channel_u8.ravel(), minlength=256)
        cdf = np.cumsum(hist)
        non_zero = cdf[cdf > 0]
        if non_zero.size == 0:
            return channel_u8.astype(np.float64)
        cdf_min = int(non_zero[0])
        total = int(channel_u8.size)
        denom = total - cdf_min
        if denom <= 0:
            return channel_u8.astype(np.float64)
        lut = np.clip(np.rint((cdf - cdf_min) / denom * 255.0), 0, 255).astype(np.float64)
        return lut[channel_u8]

    @staticmethod
    def histogram_equalization_rgb(buffer: BufferWrapper, progress_callback=None) -> BufferWrapper:
        ImageAlgorithms._report(progress_callback, 10)
        u8 = buffer.to_uint8()
        if buffer.channels == 1:
            out = ImageAlgorithms._equalize_channel_u8(u8)
            ImageAlgorithms._report(progress_callback, 100)
            return BufferWrapper(out)

        out = np.zeros_like(buffer.data)
        for c in range(buffer.channels):
            out[:, :, c] = ImageAlgorithms._equalize_channel_u8(u8[:, :, c])
            ImageAlgorithms._report(progress_callback, 10 + int((c + 1) * 90 / buffer.channels))
        return BufferWrapper(out)

    @staticmethod
    def histogram_equalization_hsv(buffer: BufferWrapper, progress_callback=None) -> BufferWrapper:
        ImageAlgorithms._report(progress_callback, 10)
        if buffer.channels == 1:
            out = ImageAlgorithms._equalize_channel_u8(buffer.to_uint8())
            ImageAlgorithms._report(progress_callback, 100)
            return BufferWrapper(out)

        h, s, v = buffer.rgb_to_hsv()
        ImageAlgorithms._report(progress_callback, 40)
        v_u8 = np.clip(np.rint(v * 255.0), 0, 255).astype(np.uint8)
        v_eq = ImageAlgorithms._equalize_channel_u8(v_u8) / 255.0
        ImageAlgorithms._report(progress_callback, 70)
        out = BufferWrapper.hsv_to_rgb(h, s, v_eq)
        ImageAlgorithms._report(progress_callback, 100)
        return BufferWrapper(out)

    @staticmethod
    def _compute_tile_lut(tile_u8: np.ndarray, clip_limit: float) -> np.ndarray:
        hist = np.bincount(tile_u8.ravel(), minlength=256).astype(np.int64)
        tile_area = int(tile_u8.size)
        limit = max(1, int(clip_limit * tile_area / 256.0))

        excess = np.maximum(hist - limit, 0)
        total_excess = int(np.sum(excess))
        hist = np.minimum(hist, limit)

        avg_inc = total_excess // 256
        rem = total_excess % 256
        hist += avg_inc
        if rem > 0:
            step = max(1, 256 // rem)
            indices = np.arange(0, 256, step)[:rem]
            hist[indices] += 1

        cdf = np.cumsum(hist)
        non_zero = cdf[cdf > 0]
        if non_zero.size == 0:
            return np.arange(256, dtype=np.float64)
        cdf_min = int(non_zero[0])
        denom = tile_area - cdf_min
        if denom <= 0:
            return np.arange(256, dtype=np.float64)
        return np.clip(np.rint((cdf - cdf_min) / denom * 255.0), 0, 255).astype(np.float64)

    @staticmethod
    def _clahe_channel(channel_u8: np.ndarray, clip_limit: float, grid_size: int, edge_mode: str, progress_callback=None) -> np.ndarray:
        h, w = channel_u8.shape
        g = max(2, int(grid_size))
        tile_h = math.ceil(h / g)
        tile_w = math.ceil(w / g)
        pad_h = tile_h * g - h
        pad_w = tile_w * g - w

        chan_buf = BufferWrapper(channel_u8)
        padded = chan_buf.pad(0, pad_h, 0, pad_w, mode=edge_mode).astype(np.uint8)

        luts = np.zeros((g, g, 256), dtype=np.float64)
        workers = min(os.cpu_count() or 4, 8)

        def tile_task(coords):
            ty, tx = coords
            y0, y1 = ty * tile_h, (ty + 1) * tile_h
            x0, x1 = tx * tile_w, (tx + 1) * tile_w
            return ty, tx, ImageAlgorithms._compute_tile_lut(padded[y0:y1, x0:x1], clip_limit)

        tile_coords = [(ty, tx) for ty in range(g) for tx in range(g)]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for idx, (ty, tx, lut) in enumerate(pool.map(tile_task, tile_coords), start=1):
                luts[ty, tx] = lut
                if progress_callback is not None and idx % max(1, len(tile_coords) // 10) == 0:
                    ImageAlgorithms._report(progress_callback, 15 + int(30 * idx / len(tile_coords)))

        xs = (np.arange(w, dtype=np.float64) + 0.5) / tile_w - 0.5
        tx0 = np.clip(np.floor(xs).astype(np.int32), 0, g - 1)
        tx1 = np.clip(tx0 + 1, 0, g - 1)
        wx = np.clip(xs - tx0, 0.0, 1.0)[None, :]

        out = np.zeros((h, w), dtype=np.float64)
        chunk_count = min(workers * 2, h)
        chunk_size = math.ceil(h / chunk_count)

        def interp_strip(y_start: int, y_end: int):
            ys = (np.arange(y_start, y_end, dtype=np.float64) + 0.5) / tile_h - 0.5
            ty0 = np.clip(np.floor(ys).astype(np.int32), 0, g - 1)[:, None]
            ty1 = np.clip(ty0 + 1, 0, g - 1)
            wy = np.clip(ys - ty0[:, 0], 0.0, 1.0)[:, None]

            vals = channel_u8[y_start:y_end, :]
            v00 = luts[ty0, tx0[None, :], vals]
            v01 = luts[ty0, tx1[None, :], vals]
            v10 = luts[ty1, tx0[None, :], vals]
            v11 = luts[ty1, tx1[None, :], vals]

            top = v00 * (1.0 - wx) + v01 * wx
            bot = v10 * (1.0 - wx) + v11 * wx
            return y_start, y_end, top * (1.0 - wy) + bot * wy

        strips = [(y, min(h, y + chunk_size)) for y in range(0, h, chunk_size)]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(interp_strip, y0, y1) for y0, y1 in strips]
            for idx, fut in enumerate(futures, start=1):
                y0, y1, block = fut.result()
                out[y0:y1, :] = block
                ImageAlgorithms._report(progress_callback, 45 + int(45 * idx / len(strips)))

        return np.clip(out, 0.0, 255.0)

    @staticmethod
    def clahe(
        buffer: BufferWrapper,
        clip_limit: float = 2.0,
        grid_size: int = 8,
        edge_mode: str = "reflect",
        progress_callback=None,
    ) -> BufferWrapper:
        ImageAlgorithms._report(progress_callback, 5)
        if buffer.channels == 1:
            out = ImageAlgorithms._clahe_channel(
                buffer.to_uint8(), clip_limit, grid_size, edge_mode, progress_callback
            )
            ImageAlgorithms._report(progress_callback, 100)
            return BufferWrapper(out)

        h, s, v = buffer.rgb_to_hsv()
        ImageAlgorithms._report(progress_callback, 15)
        v_u8 = np.clip(np.rint(v * 255.0), 0, 255).astype(np.uint8)
        v_eq = ImageAlgorithms._clahe_channel(v_u8, clip_limit, grid_size, edge_mode, progress_callback) / 255.0
        out = BufferWrapper.hsv_to_rgb(h, s, v_eq)
        ImageAlgorithms._report(progress_callback, 100)
        return BufferWrapper(out)

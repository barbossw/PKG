import numpy as np


class BufferWrapper:
    def __init__(self, data: np.ndarray):
        self.data = np.asarray(data, dtype=np.float64)
        if self.data.ndim == 2:
            self.height, self.width = self.data.shape
            self.channels = 1
        elif self.data.ndim == 3:
            self.height, self.width, self.channels = self.data.shape
        else:
            raise ValueError("Unsupported image dimensions")

    @staticmethod
    def _build_indices(length: int, pad_before: int, pad_after: int, mode: str) -> np.ndarray:
        coords = np.arange(-pad_before, length + pad_after, dtype=np.int64)
        if length <= 1:
            return np.zeros_like(coords)
        if mode == "reflect":
            period = 2 * (length - 1)
            rem = np.abs(coords) % period
            return np.where(rem >= length, period - rem, rem)
        return np.clip(coords, 0, length - 1)

    def pad(self, pad_top: int, pad_bottom: int, pad_left: int, pad_right: int, mode: str = "reflect") -> np.ndarray:
        row_idx = self._build_indices(self.height, pad_top, pad_bottom, mode)
        col_idx = self._build_indices(self.width, pad_left, pad_right, mode)
        if self.channels == 1:
            return self.data[np.ix_(row_idx, col_idx)].copy()
        return self.data[row_idx[:, None], col_idx[None, :], :].copy()

    def to_uint8(self) -> np.ndarray:
        return np.clip(np.rint(self.data), 0, 255).astype(np.uint8)

    def to_grayscale(self) -> np.ndarray:
        if self.channels == 1:
            return self.data.copy()
        return (
            0.299 * self.data[:, :, 0]
            + 0.587 * self.data[:, :, 1]
            + 0.114 * self.data[:, :, 2]
        )

    def rgb_to_hsv(self):
        rgb = np.clip(self.data, 0.0, 255.0) / 255.0
        r = rgb[:, :, 0]
        g = rgb[:, :, 1]
        b = rgb[:, :, 2]

        c_max = np.maximum(np.maximum(r, g), b)
        c_min = np.minimum(np.minimum(r, g), b)
        delta = c_max - c_min

        h = np.zeros_like(c_max)
        mask = delta > 1e-12

        r_mask = mask & (c_max == r)
        g_mask = mask & (c_max == g) & (~r_mask)
        b_mask = mask & (~r_mask) & (~g_mask)

        h[r_mask] = 60.0 * (((g[r_mask] - b[r_mask]) / delta[r_mask]) % 6.0)
        h[g_mask] = 60.0 * (((b[g_mask] - r[g_mask]) / delta[g_mask]) + 2.0)
        h[b_mask] = 60.0 * (((r[b_mask] - g[b_mask]) / delta[b_mask]) + 4.0)

        s = np.zeros_like(c_max)
        nz_max = c_max > 1e-12
        s[nz_max] = delta[nz_max] / c_max[nz_max]

        v = c_max
        return h, s, v

    @staticmethod
    def hsv_to_rgb(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
        c = v * s
        h_sector = (h / 60.0) % 6.0
        x = c * (1.0 - np.abs((h_sector % 2.0) - 1.0))
        m = v - c

        sector = np.floor(h_sector).astype(np.int32)
        r1 = np.zeros_like(v)
        g1 = np.zeros_like(v)
        b1 = np.zeros_like(v)

        m0 = sector == 0
        m1 = sector == 1
        m2 = sector == 2
        m3 = sector == 3
        m4 = sector == 4
        m5 = sector == 5

        r1[m0], g1[m0], b1[m0] = c[m0], x[m0], 0.0
        r1[m1], g1[m1], b1[m1] = x[m1], c[m1], 0.0
        r1[m2], g1[m2], b1[m2] = 0.0, c[m2], x[m2]
        r1[m3], g1[m3], b1[m3] = 0.0, x[m3], c[m3]
        r1[m4], g1[m4], b1[m4] = x[m4], 0.0, c[m4]
        r1[m5], g1[m5], b1[m5] = c[m5], 0.0, x[m5]

        rgb = np.stack((r1 + m, g1 + m, b1 + m), axis=-1)
        return np.clip(rgb * 255.0, 0.0, 255.0)

    def compute_histograms(self) -> dict:
        u8 = self.to_uint8()
        if self.channels == 1:
            luma = np.bincount(u8.ravel(), minlength=256)
            return {"r": luma, "g": luma, "b": luma, "luma": luma}
        luma_u8 = np.clip(np.rint(self.to_grayscale()), 0, 255).astype(np.uint8)
        return {
            "r": np.bincount(u8[:, :, 0].ravel(), minlength=256),
            "g": np.bincount(u8[:, :, 1].ravel(), minlength=256),
            "b": np.bincount(u8[:, :, 2].ravel(), minlength=256),
            "luma": np.bincount(luma_u8.ravel(), minlength=256),
        }

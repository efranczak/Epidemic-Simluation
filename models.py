import numpy as np
import math
from abc import ABC, abstractmethod


class Model(ABC):

    @abstractmethod
    def step(self, dt: float) -> None: ...

    @abstractmethod
    def get_field(self) -> np.ndarray:
        """Returns an array for plotting"""

    def info(self) -> str:
        return ""



class Diffusion(Model):
    def __init__(self, n=100, D=1.0):
        self.u = np.zeros((n, n))
        self.u[n // 2 - 5:n // 2 + 5, n // 2 - 5:n // 2 + 5] = 1.0
        self.D = D
        self.t = 0.0

    def step(self, dt):
        u = self.u
        lap = (np.roll(u, 1, 0) + np.roll(u, -1, 0) +
               np.roll(u, 1, 1) + np.roll(u, -1, 1) - 4 * u)
        self.u = u + self.D * dt * lap
        self.t += dt

    def get_field(self):
        return self.u

    def info(self):
        return f"t = {self.t:.2f}"

class SEIR(Model):
    S_VAL, E_VAL, I_VAL, R_VAL = 0, 1, 2, 3

    __slots__ = ("S", "I", "R", "E", "N", "t",
                 "infectionFactor", "infectionPeroid", "incubationPeroid",
                 "immunityPeroid", "lethality", "naturalLethality",
                 "beta", "gamma", "sigma", "omega", "R0",
                 "center", "gridSize", "visualArrays")

    def __init__(self, S: int, I: int, R: int, E: int,
                 infectionFactor: float, infectionPeroid: float, incubationPeroid: float,
                 immunityPeroid: float, lethality: float, naturalLethality: float):
        self.S, self.E, self.I, self.R = float(S), float(E), float(I), float(R)
        self.N = self.S + self.E + self.I + self.R
        self.t = 0.0

        self.infectionFactor = infectionFactor
        self.infectionPeroid = infectionPeroid
        self.incubationPeroid = incubationPeroid
        self.immunityPeroid = immunityPeroid
        self.lethality = lethality
        self.naturalLethality = naturalLethality

        # Rates (per time unit)
        self.beta = infectionFactor
        self.gamma = 1.0 / infectionPeroid
        self.sigma = 1.0 / incubationPeroid
        self.omega = 1.0 / immunityPeroid if immunityPeroid > 0 else 0.0

        mu, alpha = naturalLethality, lethality
        self.R0 = (self.sigma / (self.sigma + mu)) * (self.beta / (self.gamma + mu + alpha))

        self.center = None
        self.gridSize = math.isqrt(int(self.N))
        self.visualArrays = None

    def step(self, dt: float):
        S, E, I, R, N = self.S, self.E, self.I, self.R, self.N
        beta, sigma, gamma, omega = self.beta, self.sigma, self.gamma, self.omega
        mu, alpha = self.naturalLethality, self.lethality

        infections = beta * I * S / N if N > 0 else 0.0

        dS = mu * N - infections + omega * R - mu * S
        dE = infections - sigma * E - mu * E
        dI = sigma * E - gamma * I - (mu + alpha) * I
        dR = gamma * I - omega * R - mu * R

        self.S = max(S + dS * dt, 0.0)
        self.E = max(E + dE * dt, 0.0)
        self.I = max(I + dI * dt, 0.0)
        self.R = max(R + dR * dt, 0.0)
        self.N = self.S + self.E + self.I + self.R
        self.t += dt

    def SetCenter(self, center: tuple[int, int]):
        self.center = center

    def MapIntoArrays(self, layer: int = 0) -> np.ndarray:
        size = self.gridSize
        total = size * size

        values_order = np.array([self.R_VAL, self.I_VAL, self.E_VAL, self.S_VAL])
        counts = np.clip(np.array([self.R, self.I, self.E, self.S], dtype=float), 0, None)

        if counts.sum() > 0:
            exact = counts / counts.sum() * total
        else:
            exact = np.array([0, 0, 0, total], dtype=float)
        cells = np.floor(exact).astype(int)
        leftover = total - cells.sum()
        cells[np.argsort(exact - cells)[::-1][:leftover]] += 1

        cy, cx = self.center if self.center is not None else (size // 2, size // 2)
        yy, xx = np.indices((size, size))
        dist = (yy - cy) ** 2 + (xx - cx) ** 2
        angle = np.arctan2(yy - cy, xx - cx)
        cell_order = np.lexsort((angle.ravel(), dist.ravel()))

        grid = np.empty(total, dtype=np.int8)
        grid[cell_order] = np.repeat(values_order, cells)
        grid = grid.reshape(size, size)

        if self.visualArrays is None or self.visualArrays.shape[1:] != (size, size):
            self.visualArrays = np.zeros((layer + 1, size, size), dtype=np.int8)
        elif layer >= self.visualArrays.shape[0]:
            extra = np.zeros((layer + 1 - self.visualArrays.shape[0], size, size), dtype=np.int8)
            self.visualArrays = np.concatenate([self.visualArrays, extra])
        self.visualArrays[layer] = grid
        return grid

    def get_field(self):
        return self.MapIntoArrays(0)

    def info(self):
        return (f"t = {self.t:.1f}  R0 = {self.R0:.2f}  "
                f"S={self.S:.0f} E={self.E:.0f} I={self.I:.0f} R={self.R:.0f}")
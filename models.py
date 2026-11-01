import numpy as np
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



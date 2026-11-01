from models import Diffusion
from utility import run_realtime


def main():
    run_realtime(Diffusion(n=60, D=1.0), dt=0.2, v_min=0, v_max=1)

if __name__ == '__main__':
    main()
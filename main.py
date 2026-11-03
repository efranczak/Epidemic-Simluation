from models import SEIR
from utility import run_realtime

def main():
    run_realtime(SEIR(S=9990, I=10, R=0, E=0,
             infectionFactor=0.5,     
             infectionPeroid=7,    
             incubationPeroid=5,     
             immunityPeroid=180,     
             lethality=0.002,
             naturalLethality=1/(70*365)))

if __name__ == '__main__':
    main()
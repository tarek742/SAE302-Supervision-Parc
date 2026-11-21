#!/usr/bin/python3
from collecte import recuperer_metrique

if __name__ == "__main__":
    while True:
        metrique = recuperer_metrique()
        print(metrique)
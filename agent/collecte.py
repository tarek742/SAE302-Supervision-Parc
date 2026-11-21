#!/usr/bin/python3
import psutil, os, time

def recuperer_metrique():
    cpu = psutil.cpu_percent(interval=1)

    ram = psutil.virtual_memory().percent
    

    if os.name == 'nt':
        chemin_disque = 'C:\\' 
    else:
        chemin_disque = '/'     

    disque = psutil.disk_usage(chemin_disque).percent

    Ancien_octets_envoyés = psutil.net_io_counters().bytes_sent
    Ancien_octets_reçus = psutil.net_io_counters().bytes_recv
    
    time.sleep(9)
    
    Diff_octets_envoyés = psutil.net_io_counters().bytes_sent - Ancien_octets_envoyés
    Diff_octets_reçus = psutil.net_io_counters().bytes_recv - Ancien_octets_reçus

    infos = {"cpu":cpu, "ram":ram, "disque":disque, "octets_envoyes":Diff_octets_envoyés, "octets_recus":Diff_octets_reçus}
    return infos

while True:
    metrique = recuperer_metrique()
    print(metrique)

    
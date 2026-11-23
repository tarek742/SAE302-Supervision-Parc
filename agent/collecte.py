#!/usr/bin/python3
import psutil, os, time

def recuperer_metrique():
    cpu_pct = psutil.cpu_percent(interval=1)

    ram_pct = psutil.virtual_memory().percent
    

    if os.name == 'nt':
        chemin_disque = 'C:\\' 
    else:
        chemin_disque = '/'     

    disk_pct = psutil.disk_usage(chemin_disque).percent

    Ancien_octets_envoyés = psutil.net_io_counters().bytes_sent
    Ancien_octets_reçus = psutil.net_io_counters().bytes_recv
    
    time.sleep(9)
    
    net_sent_bytes = psutil.net_io_counters().bytes_sent - Ancien_octets_envoyés
    net_recv_bytes = psutil.net_io_counters().bytes_recv - Ancien_octets_reçus

    infos = {"cpu":cpu_pct, "ram":ram_pct, "disque":disk_pct, "octets_envoyes":net_sent_bytes, "octets_recus":net_recv_bytes}
    return infos

while True:
    metrique = recuperer_metrique()
    print(metrique)

    
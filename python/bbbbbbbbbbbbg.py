# -*- coding: utf-8 -*-
"""
Created on Sat May 24 11:15:19 2025

@author: junio
"""


import pandas as pd
import pyreadstat

def eviews_to_csv(input_file, output_file):
    """
    Convertit un fichier EViews (.wf1) en fichier CSV
    
    Args:
        input_file (str): Chemin vers le fichier EViews d'entrée
        output_file (str): Chemin vers le fichier CSV de sortie
    """
    try:
        # Lire le fichier EViews
        df, meta = pyreadstat.read_file(input_file)
        
        # Écrire le DataFrame dans un fichier CSV
        df.to_csv(output_file, index=False)
        
        print(f"Conversion réussie! Fichier CSV sauvegardé sous: {output_file}")
    
    except Exception as e:
        print(f"Erreur lors de la conversion: {str(e)}")

# Exemple d'utilisation
input_path = "C:/Users/junio/Documents/M1 DATA Semester2/Capstone/ultime"  # Remplacez par votre fichier EViews
output_path = "C:/Users/junio/Documents/M1 DATA Semester2/Capstone"  # Chemin de sortie souhaité

eviews_to_csv(input_path, output_path)
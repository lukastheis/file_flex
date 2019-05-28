# -*- coding: utf-8 -*-
"""
Created on Thu May 16 08:12:02 2019

@author: theisinger_l
"""
#model_name="Bibliothek.Simulationswerkzeug.Modelle.Waerme"
#model_path='C:/Users/theisinger_l/Bibliothek.mo'
#param_dict={"konf_BHKW":"true","konf_WRG":"false","konf_Pufferspeicher":"true","Anzahl_WRG":"0","Anzahl_HK":"45"}
from dymola.dymola_interface import DymolaInterface
from dymola.dymola_exception import DymolaException
#sind in dem dictionary stets alle möglichen Parameter enthalten und jeweils mit Booleans/Reals besetzt oder willsd du für die verschiedenen Flexibilisierungsmaßnahmen verschiedene dicts erzeugen?
def simulate_flex(model_name,model_path,sim_duration,flex_var,param_dict):
    
    dymola = DymolaInterface()
    #Model muss noch geöffnet sein
    openModel=dymola.openModel(path=model_path)
    print(openModel)

    translateModel=dymola.translateModel(problem=model_name)
    print(translateModel)
    
    if flex_var==1:
        #erste Ebene
        dymola.ExecuteCommand("konf_Bivalenz=true")
        dymola.ExecuteCommand("konf_HK=true")
        dymola.ExecuteCommand("konf_BHKW_stromgefuehrt=false")
        #zweite Ebene
        dymola.ExecuteCommand(str("konf_BHKW="+param_dict["konf_BHKW"]))
        dymola.ExecuteCommand(str("konf_WRG="+param_dict["konf_WRG"]))
        dymola.ExecuteCommand(str("konf_Puffer="+param_dict["konf_Puffer"]))
        dymola.ExecuteCommand(str("Anzahl_HK="+param_dict["Anzahl_HK"]))
    
        #die if-Bedingung ist nur zur Sicherheit        
        if param_dict["konf_WRG"]=="true":
            dymola.ExecuteCommand(str("Anzahl_WRG="+param_dict["Anzahl_WRG"])) 
        else:
            dymola.ExecuteCommand("Anzahl_WRG=0")
        
        
    elif flex_var==2:
        #erste Ebene
        dymola.ExecuteCommand("konf_BHKW=true")
        dymola.ExecuteCommand("konf_Bivalenz=false")
        dymola.ExecuteCommand("konf_BHKW_Puffer=true")
        dymola.ExecuteCommand("konf_BHKW_stromgefuehrt=true")
        #zweite Ebene
        dymola.ExecuteCommand(str("konf_HK="+param_dict["konf_HK"]))
        dymola.ExecuteCommand(str("konf_WRG="+param_dict["konf_WRG"]))
        
        #die if-Bedingung ist nur zur Sicherheit 
        if param_dict["konf_HK"]=="true":
            dymola.ExecuteCommand(str("Anzahl_HK="+param_dict["Anzahl_HK"]))
        else:
            dymola.ExecuteCommand("Anzahl_HK=0")
        
        #die if-Bedingung ist nur zur Sicherheit
        if param_dict["konf_WRG"]=="true":
            dymola.ExecuteCommand(str("Anzahl_WRG="+param_dict["Anzahl_WRG"])) 
        else:
            dymola.ExecuteCommand("Anzahl_WRG=0") 
        
        
        
    else:
        print("Auswahl der Flexibilisierungsmaßnahme fehlerhaft")
    result=dymola.simulateExtendedModel(problem=model_name,stopTime=sim_duration,finalNames=["konf_Bivalenz","konf_HK","konf_BHKW_stromgefuehrt","konf_BHKW","konf_WRG","konf_Puffer","Anzahl_WRG","Anzahl_HK"])
    if not result[0]:
                    print("Simulation failed. Below is the translation log.")
                    log = dymola.getLastError()
                    print(log)
    print('ERGEBNIS_Inhalt:',"konf_Bivalenz","konf_HK","konf_BHKW_stromgefuehrt","konf_BHKW","konf_WRG","konf_Puffer","Anzahl_WRG","Anzahl_HK")
    #saveModel=dymola.saveTotalModel('C:/Users/theisinger_l/waerme_save.mo', "waerme")
    #Achtung Dymola speichert mit saveTotalModel anscheinend nicht parameterwerte ab..
    #print(saveModel)
    dymola.close()
    return result

            
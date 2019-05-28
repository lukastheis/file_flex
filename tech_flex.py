# -*- coding: utf-8 -*-
"""
Created on Thu May 23 09:25:18 2019

@author: theisinger_l
"""

import csv
import numpy as np
import os
import matplotlib.pyplot as plt
import scipy.io as sio
from modelicares import SimRes

from dymola.dymola_interface import DymolaInterface
from dymola.dymola_exception import DymolaException

Root=os.getcwd()
Root_daten=Root+'\daten'
Root_modelle=Root+'\modelle'
Root_simulationsergebnisse=Root+'\simulationsergebnisse'
Root_kennfelder=Root+'\kennfelder'

print(Root_daten)

name_strompreis='strompreis.csv'
name_lastfall='lastfall.csv'
name_laden_daten='laden_daten.csv'
name_modell_sim='kaelteanlage_lebensmittelindustrie.kaelteanlage_eissilo'
#name_modell_sim='kaelteanlage_niedertemperatur.kaelteanlage_eisbank'

name_modell_kenn='kaelteanlage_lebensmittelindustrie.kaelteanlage_eissilo_kennfeldgenerierung'
#name_modell_kenn='kaelteanlage_niedertemperatur.kaelteanlage_eisbank_kennfeldgenerierung'
name_txtfile='lastfall'


dir_strompreis=os.path.join(Root_daten,name_strompreis)
dir_modell_sim=os.path.join(Root_modelle,name_modell_sim)+'.mo'
dir_modell_kenn=os.path.join(Root_modelle,name_modell_kenn)+'.mo'
dir_lastfall=os.path.join(Root_daten,name_lastfall)
dir_laden_daten=os.path.join(Root_daten,name_laden_daten)
dir_txtfile=os.path.join(Root_modelle,name_txtfile)


print(dir_modell_kenn)
print(dir_strompreis)

txt_file_name='lastfall'


#Erzeugt die Arrays, welche Maxima, Minima und Ladphasen enthalten + die Simulationsdauer wird ausgegeben
def anfangsanalyse(pfad):
    
    reader=csv.reader(open(pfad),delimiter=";")#Einlesen des Strompreises
    x=list(reader)
    strompreis=np.array(x).astype("float")
    
    plt.plot(strompreis[:,0],strompreis[:,1])
    dauer=strompreis[:,0][len(strompreis)-1]
    
    preis_verlauf=strompreis[:,1]
    
    #Hier werden die Extrema gesucht ... ACHTUNG: wenn minium aus mehreren gleichen Werten besteht funktioniert das nicht --> Skript zur anpassung des Strompreises schreiben
    minimum=np.r_[True, preis_verlauf[1:] < preis_verlauf[:-1]] & np.r_[preis_verlauf[:-1]<preis_verlauf[1:],True]
    minimum,=np.where(minimum==True)
    maximum=np.r_[True, preis_verlauf[1:]>preis_verlauf[:-1]] & np.r_[preis_verlauf[:-1]>preis_verlauf[1:],True]
    maximum,=np.where(maximum==True)
    
    print(minimum)
    print(maximum)
    #Löschen des ersten Minimums, wenn dieses bei t=0 liegt
    if strompreis[0,1]<strompreis[1,1]:
        minimum=minimum[1:]
    #Löschen des ersten Maximums, wenn dieses bei t=0 liegt
    if strompreis[0,1]>strompreis[1,1]:
        maximum=maximum[1:]
    #Löschen des letzten Minimums, wenn dieses an letzter stelle liegt
    if strompreis[len(strompreis)-1,1]<strompreis[len(strompreis)-2,1]:
        minimum=minimum[:len(minimum)-1]
    #Löschen des letzten Maximums, wenn dieses an letztes stelle liegt
    if strompreis[len(strompreis)-1,1]>strompreis[len(strompreis)-2,1]:
        maximum=maximum[:len(maximum)-1]
        
    
    
    #ladephasen wird als array definiert --> Zeile steht für den betrachteten Zyklus
    
    
    if maximum[0]<minimum[0]:
        maximum=maximum[1:]
    if minimum[len(minimum)-1]>maximum[len(maximum)-1]:
        minimum=minimum[:len(minimum)-1]
    ladephase=np.zeros((len(minimum),2))
    
    
    if len(maximum)==len(minimum):
        count=1
        diff_links=0
        diff_rechts=0
        diff_min=0
        while count<len(minimum)+1:
            if count>1:
                diff_links=minimum[count-1]-maximum[count-2]
                diff_rechts=maximum[count-1]-minimum[count-1]
                print(diff_min)
                diff_min=min(diff_links,diff_rechts)
                ladephase[count-1,0]=minimum[count-1]-diff_min
                ladephase[count-1,1]=minimum[count-1]+diff_min
            if count==1:
                if maximum[count-1]-minimum[count-1]>minimum[count-1]:
                    diff_min=minimum[count-1]
                else:
                    diff_min=maximum[count-1]-minimum[count-1]
                print(diff_min)
                ladephase[count-1,0]=minimum[count-1]-diff_min
                ladephase[count-1,1]=minimum[count-1]+diff_min
            count=count+1       
            
    if len(maximum)>len(minimum):
        count=1
        diff_links=0
        diff_rechts=0
        diff_min=0
        while count<len(minimum)+1:
            diff_links=minimum[count-1]-maximum[count-1]
            diff_rechts=maximum[count]-minimum[count-1]
            diff_min=min(diff_links,diff_rechts)
            ladephase[count-1,0]=minimum[count-1]-diff_min
            ladephase[count-1,1]=minimum[count-1]+diff_min
            
            count=count+1
            
     #Ausgegeben sollen nur die Maxima und Minima werden, welche bei der Optimierung auch behandelt werden
    
    
    return minimum,maximum,ladephase,dauer

#sucht sich aus der Massenstrom-Excel und den Maxima/Minima die entsprechenden Werte zur Kennfelderzeugung
def get_massenstrom(liste_minima,liste_maxima,massenstrom):
    array_massenstrom_laden=np.zeros((len(liste_minima),1))
    array_massenstrom_entladen=np.zeros((len(liste_maxima),1))
    for i in range(len(liste_minima)):
        array_massenstrom_laden[i]=massenstrom[np.where(liste_minima[i]==massenstrom[:,0])[0],1]
    for i in range(len(liste_maxima)):
        array_massenstrom_entladen[i]=massenstrom[np.where(liste_maxima[i]==massenstrom[:,0])[0],1]
    return array_massenstrom_laden,array_massenstrom_entladen

#erzeugt aus dem Array ein txtfile, welches dymola lesen kann ---> wird wohl so nicht mehr benötigt
def array_to_txt(array,dir_txtfile):
    string_header=np.empty((2,2),dtype=object)
    string_header[0,0]='#1'
    string_header[0,1]=''
    string_header[1,0]='double'
    string_header[1,1]='tab1'+str(np.shape(array))
    
    string_basis=np.empty(np.shape(array),dtype=object)
    for i in range(len(array)):
        string_basis[i,0]=str(array[i,0])
        string_basis[i,1]=str(array[i,1])
    string_merge=np.vstack((string_header,string_basis))
    np.savetxt(dir_txtfile+'.txt',string_merge,delimiter=" ", fmt="%s")
    return

#erzeugt das kennfeld
def create_kennfeld(array_massenstrom_laden,array_massenstrom_entladen,Root_simulationsergebnisse,model_kennfeld_path,model_kennfeld_name,Root_modelle,Root_kennfelder):
    array_drop=np.zeros((2,2))
    array_drop[0,0]=0
    array_drop[0,1]=array_massenstrom_laden[0]
    array_drop[1,0]=200
    array_drop[1,1]=array_massenstrom_laden[0]
    array_to_txt(array_drop,os.path.join(Root_modelle,'lastfall_kennfeld'))
    kennfeld_simulieren(array_massenstrom_laden[0][0],Root_simulationsergebnisse,model_kennfeld_path,model_kennfeld_name)
    kennfeld_erzeugen(array_massenstrom_laden[0][0],Root_kennfelder,Root_simulationsergebnisse)
    bereits_enthalten=[[2000000]]
    for i in range(len(array_massenstrom_entladen)):
        if array_massenstrom_entladen[i] not in bereits_enthalten:
            print('erstellt wird',array_massenstrom_entladen[i])
            array_drop=np.zeros((2,2))
            array_drop[0,0]=0
            array_drop[0,1]=array_massenstrom_entladen[i]
            array_drop[1,0]=200
            array_drop[1,1]=array_massenstrom_entladen[i]
            array_to_txt(array_drop,os.path.join(Root_modelle,'lastfall_kennfeld'))
            kennfeld_simulieren(array_massenstrom_entladen[i][0],Root_simulationsergebnisse,model_kennfeld_path,model_kennfeld_name)
            kennfeld_erzeugen(array_massenstrom_entladen[i][0],Root_kennfelder,Root_simulationsergebnisse) 
            bereits_enthalten=np.vstack((bereits_enthalten,array_massenstrom_entladen[i]))
            print('bereits_enthalten',bereits_enthalten)
            
    return

#erzeugt ein Array, welches die die Speicherorte der Kennfelder enthält --> damit kann vernünftig iteriert werden
def create_kennfeldnamen(array_massenstrom_laden,array_massenstrom_entladen,Root_kennfelder):
    array_names=np.zeros((len(array_massenstrom_laden),2),dtype=object)
    for i in range(len(array_massenstrom_laden)):
        array_names[i,0]=os.path.join(Root_kennfelder,'kennfeld_mp'+str(array_massenstrom_laden[i][0]))
        array_names[i,1]=os.path.join(Root_kennfelder,'kennfeld_mp'+str(array_massenstrom_entladen[i][0]))
    return array_names

#Simulation welche zur Kennfelderstellung benötigt wird, wird durchgeführt
def kennfeld_simulieren(mp,Root_simulationsergebnisse,model_kennfeld_path,model_kennfeld_name):
    dymola = None
    try:
        #erzeuge Instanz von Dymola
        dymola = DymolaInterface()
    
        print(model_kennfeld_path,model_kennfeld_name)
        #öffne das Model
        dymola.openModel(path=model_kennfeld_path)
        dymola.translateModel(problem=model_kennfeld_name)
        print('simulieren')
        result = dymola.simulateExtendedModel(problem=model_kennfeld_name,stopTime=200000,method='radau IIa',resultFile=Root_simulationsergebnisse+'\simulationsergebnis_mp'+str(mp))
        print(result[0])
        if not result:
            print("Simulation failed. Below is the translation log.")
            log = dymola.getLastError()
            print(log)
    except DymolaException as ex:
        print("Error: " + str(ex))
    
    if dymola is not None:
        dymola.close()
        dymola = None
    return
    
#Kennfeld wird aus SImulationsergebnissen erstellt und als Mat Datei gespeichert
def kennfeld_erzeugen(mp,Root_kennfelder,Root_simulationsergebnisse):
#ergebnisse sind in mat datei gespeichert und enthalten die Simulationszeit, den SOC , sowie den Zustand, welcher bei 1 laden und 0 entladen bedeutet
#Simulationsergebnis muss so vorliegen, dass speicher anfangs entladen ist
    sim=SimRes(os.path.join(Root_simulationsergebnisse,'simulationsergebnis_mp'+str(mp)+'.mat'))
    zeit=sim['Time']
    zeit=zeit.values()
    SOC=sim['SOC']
    SOC=SOC.values()
    SOC=np.vstack((zeit,SOC))
    SOC=np.transpose(SOC)
    print(SOC)
    zustand=sim['zustand.Q']
    zustand=zustand.values()
    zustand=np.vstack((zeit,zustand))
    #zustand ist array welches zeit und entladezustand enthält
    zustand=np.transpose(zustand)
    print(zustand)
    a=1
    entladen_start=np.zeros((1,1))
    #zeitstempel der Entlade-Anfänge werden gesucht
    while a<len(zustand):
        if zustand[a,1]<zustand[a-1,1]:
            entladen_start=np.vstack((entladen_start,zustand[a,0]))
        a=a+1
    
    entladen_start=entladen_start[2:,:] #enthält die Zeitstempel, wann das Entladen beginnt
    print('entladen start:',entladen_start)
    b=1
    laden_start=np.zeros((1,1))
    #zeitstempel der Lade-Anfänge werden gesucht
    while b<len(zustand):
        if zustand[b,1]>zustand[b-1,1]:
            laden_start=np.vstack((laden_start,zustand[b,0]))
        b=b+1
    laden_start=laden_start[2:,:] #enthält die Zeitstempel, wann das Laden beginnt
    print('laden start:',laden_start)
    
    #Hier wird das Ladekennfeld erstellt
    anfang_laden=np.where(zustand==laden_start[0])
    anfang_laden=anfang_laden[0]
    anfang_laden=anfang_laden[1]
    print('anfang laden',anfang_laden)
    
    ende_laden=np.where(zustand==entladen_start[1])
    #print('ende',ende)
    ende_laden=ende_laden[0]
    ende_laden=ende_laden[1]
    print('ende laden',ende_laden)
    
    
    laden=np.zeros((ende_laden-anfang_laden+1,2))
    laden[:,0]=zeit[anfang_laden:ende_laden+1]
    laden[:,1]=SOC[anfang_laden:ende_laden+1,1]
    #print(laden)
    
    #das hier ist unschön --> glättet aber das Kennfeld des Eissilos
    for i in range(10):
        for i in range(1,len(laden)):
            if laden[i,1]<laden[i-1,1]:
                laden[i-1,1]=laden[i,1]
    Abzug=laden[0,0]
    for i in range(len(laden)):
        laden[i,0]=laden[i,0]-Abzug
        
    #Hier wird das Entladekennfeld erstellt
    anfang_entladen=np.where(zustand==entladen_start[1])
    #print('anfang entladen', anfang_1)
    anfang_entladen=anfang_entladen[0]
    anfang_entladen=anfang_entladen[1]
    print('anfang entladen', anfang_entladen)
    ende_entladen=np.where(zustand==laden_start[1])
    #print('ende entladen',ende_1)
    ende_entladen=ende_entladen[0]
    ende_entladen=ende_entladen[1]
    print('ende entladen',ende_entladen)
    entladen=np.zeros((ende_entladen-anfang_entladen+1,2))
    entladen[:,0]=zeit[anfang_entladen:ende_entladen+1]
    entladen[:,1]=SOC[anfang_entladen:ende_entladen+1,1]
    
    
    Abzug=entladen[0,0]
    for i in range(len(entladen)):
        entladen[i,0]=entladen[i,0]-Abzug
    Normierung=entladen[len(entladen)-1,0]
    for i in range(len(entladen)):
        entladen[i,0]=Normierung-entladen[i,0]
    entladen_neu=np.zeros((len(entladen),2))
    for i in range(len(entladen)):
        entladen_neu[i,0]=entladen[len(entladen)-1-i,0]
        entladen_neu[i,1]=entladen[len(entladen)-1-i,1]
 
    plt.subplot(311)
    plt.plot(laden[:,0],laden[:,1])
    plt.subplot(312)
    plt.plot(entladen_neu[:,1],entladen_neu[:,0])
    
    
    sio.savemat(os.path.join(Root_kennfelder,'kennfeld_mp'+str(mp)),dict(ladekurve=laden,entladekurve=entladen_neu))
    return laden,entladen_neu,SOC

#gibt den SOC in Abhängigkeit der Ladedauer an
def get_SOC(array_names,lade_array,Zyklus):
    mat_inhalt=sio.loadmat(array_names[Zyklus-1][0])
    ladekurve=mat_inhalt['ladekurve']
    max_ladedauer=ladekurve[len(ladekurve)-1,0]
    
    #unterscheidung zwischen liste_ladephasen und einzelne Betrachtung
    if np.size(lade_array)>2:
        ladedauer=(lade_array[Zyklus-1,1]-lade_array[Zyklus-1,0])*3600
    else:
        ladedauer=(lade_array[0,1]-lade_array[0,0])*3600
    print('ladedauer',ladedauer)
    print('max_ladedauer',max_ladedauer)
    if max_ladedauer<ladedauer:
        ladedauer=max_ladedauer
    print(ladedauer)
    SOC=np.interp(ladedauer,ladekurve[:,0],ladekurve[:,1])
    return SOC

#gibt die Entladedauer in Abhängigkeit des SOC an
def get_entladedauer(array_names,SOC,Zyklus): 
    mat_inhalt=sio.loadmat(array_names[Zyklus-1][1])
    entladekurve=mat_inhalt['entladekurve']
    entladedauer=np.interp(SOC,entladekurve[:,1],entladekurve[:,0])
    return entladedauer

#gibt den  für die Entladedauer benötigten SOC an
def reverse_SOC(array_names,entladedauer,Zyklus): 
    mat_inhalt=sio.loadmat(array_names[Zyklus-1][1])
    entladekurve=mat_inhalt['entladekurve']
    SOC=np.interp(entladedauer*3600,entladekurve[:,0],entladekurve[:,1])
    return SOC

# gibt die für den SOC benötigte Ladedauer an
def reverse_ladedauer(array_names,SOC,Zyklus): 
    mat_inhalt=sio.loadmat(array_names[Zyklus-1][0])
    ladekurve=mat_inhalt['ladekurve']
    ladedauer=np.interp(SOC,ladekurve[:,1],ladekurve[:,0])
    return ladedauer

#hier wird darauf geachtet, dass sich die vorherige Entadephase nicht mit der aktuellen Ladephase überschneidet
def correct_left(ladephase,entladephase,Zyklus,Minimum):
    if Zyklus>1:
        if ladephase[Zyklus-1,0]<entladephase[Zyklus-2,1]:
            print('Überschneidung von links?:','true')
            if entladephase[Zyklus-2,1]<Minimum[Zyklus-1]:#Wenn Sich die vorherige Entladephase in die aktuelle Lade zieht wird die Ladephase entsprechend verkürzt
                ladephase[Zyklus-1,0]=(Minimum[Zyklus-1]-0.99*(Minimum[Zyklus-1]-entladephase[Zyklus-2,1]))
                ladephase[Zyklus-1,1]=(Minimum[Zyklus-1]+0.99*(Minimum[Zyklus-1]-entladephase[Zyklus-2,1]))
            elif entladephase[Zyklus-2,1]>Minimum[Zyklus-1]:#Wenn sich die vorherige Entladephase über das aktuelle Strompreisminimum zieht wird während diesem Minimum nicht beladen
                ladephase[Zyklus-1,0]=0
                ladephase[Zyklus-1,1]=0
                entladephase[Zyklus-1,0]=0
                entladephase[Zyklus-1,1]=0
    return ladephase,entladephase

#hier wird darauf geachtet, dass das Entladen des Speichers nicht schon während des Beladens beginnt
def correct_right(ladephase, entladephase, Zyklus, Maximum,Minimum,array_names):
    print('hier in correct_right',entladephase[Zyklus-1,0],ladephase[Zyklus-1,1],Zyklus)
    print(entladephase[Zyklus-1,0]<ladephase[Zyklus-1,1])
    if entladephase[Zyklus-1,0]<ladephase[Zyklus-1,1]:
        überschneidung=True
        print('Überschneidung von rechts?:',überschneidung)
        print(entladephase,ladephase)
    else: 
        überschneidung=False
    while überschneidung==True:
        entladedauer=entladephase[Zyklus-1,1]-entladephase[Zyklus-1,0]
        #print(entladedauer)
        #eismasse_alt=reverse_eismasse(pfad_kennfeld,entladedauer)
        entladedauer=entladedauer*0.9
        SOC_neu=reverse_SOC(array_names,entladedauer,Zyklus)
        #print('masse alt',eismasse_alt)
        print('SOC neu',SOC_neu)
        print('entladedauer',entladedauer)
        if SOC_neu>0: 
            ladedauer_neu=reverse_ladedauer(array_names,SOC_neu,Zyklus)
            ladephase[Zyklus-1,0]=Minimum[Zyklus-1]-(ladedauer_neu/(2*3600))
            ladephase[Zyklus-1,1]=Minimum[Zyklus-1]+(ladedauer_neu/(2*3600))
            entladephase[Zyklus-1,0]=Maximum[Zyklus-1]-(entladedauer/(3))# &&&
            entladephase[Zyklus-1,1]=Maximum[Zyklus-1]+(2*entladedauer/(3))# &&&
        else:#Ist die Ladephase so kurz, dass kein SOC gebildet werden kann wird die Ladephase nicht zur Speicherbeladung verwendet
            ladephase[Zyklus-1,0]=0
            ladephase[Zyklus-1,1]=0
            entladephase[Zyklus-1,0]=0
            entladephase[Zyklus-1,1]=0
        
        if entladephase[Zyklus-1,0]>=ladephase[Zyklus-1,1]:
                überschneidung=False
    return ladephase,entladephase

#erzeugt den input string aus den lade/entladetabellen
def merge(phasen,pfad):
    reader=csv.reader(open(pfad),delimiter=";")
    x=list(reader)
    daten=np.array(x).astype("float")
    daten_row=0
    phasen_row=0
    while phasen_row<(len(phasen)):
        daten[daten_row]=3600*phasen[phasen_row,0]
        daten[daten_row+1]=3600*phasen[phasen_row,1]
        daten_row=daten_row+2
        phasen_row=phasen_row+1
    input_string='{'
    for i in range(len(daten)-1):
        input_string=input_string+str(float(daten[i]))+','
    
    input_string=input_string[0:len(input_string)-1]
    input_string=input_string+'}'
    return input_string

def clear_phasen(phasen):
    zeros=np.where(phasen[:,1]==0)
    for i in range(len(zeros[0])):
        where=np.where(phasen[:,1]==0)
        phasen=np.delete(phasen,where[0],0)
    return phasen

    
#führt die eigentliche Optimierung durch
def optimierung(liste_minima,liste_maxima,liste_ladephasen,array_names,simulationsdauer,dir_laden_daten,dir_modell_sim,name_modell_sim,Root_simulationsergebnisse,ergebnis_compare):
    
    Zyklenanzahl=len(liste_ladephasen)
    Zyklus=1
    liste_entladephasen=np.zeros(np.shape(liste_ladephasen))
    #ein Zyklus bedeutet die Zeitdauer von Anfang eines Minimum bis zum Ende des darauffolgenden Maximums
    while Zyklus<Zyklenanzahl+1:
        print('Aktueller Strompreiszyklus in dem Optimiert wird:',Zyklus)
        SOC=get_SOC(array_names,liste_ladephasen,Zyklus)
        entladedauer=get_entladedauer(array_names,SOC,Zyklus)
        ladedauer=reverse_ladedauer(array_names,SOC,Zyklus)
        print('SOC',SOC)
        print('entladedauer',entladedauer)
        print('ladedauer',ladedauer)
        
        liste_ladephasen[Zyklus-1,0]=liste_minima[Zyklus-1]-(ladedauer/(2*3600))
        liste_ladephasen[Zyklus-1,1]=liste_minima[Zyklus-1]+(ladedauer/(2*3600))
        print('liste_ladephasen',liste_ladephasen)
        
        liste_entladephasen[Zyklus-1,0]=liste_maxima[Zyklus-1]-(entladedauer/(3*3600))# &&&
        liste_entladephasen[Zyklus-1,1]=liste_maxima[Zyklus-1]+(2*entladedauer/(3*3600))# &&&
        print('liste_entladephasen', liste_entladephasen)
        
        correct_left_result=correct_left(liste_ladephasen,liste_entladephasen,Zyklus,liste_minima)
        liste_ladephasen[Zyklus-1,:]=correct_left_result[0][Zyklus-1,:]
        liste_entladephasen[Zyklus-1,:]=correct_left_result[1][Zyklus-1,:]
        print('liste_phasen nach correct left',liste_ladephasen,liste_entladephasen)
        
        correct_right_result=correct_right(liste_ladephasen,liste_entladephasen,Zyklus,liste_maxima,liste_minima,array_names)
        liste_ladephasen[Zyklus-1,:]=correct_right_result[0][Zyklus-1,:]
        liste_entladephasen[Zyklus-1,:]=correct_right_result[1][Zyklus-1,:]
        print('liste_phasen nach correct right',liste_ladephasen,liste_entladephasen)
        
        ergebnis=np.array([[0,0]])
        
        ladedauer_neu=liste_ladephasen[Zyklus-1,1]-liste_ladephasen[Zyklus-1,0]
        print('ladedauer_neu_check',ladedauer_neu)
        better=True
        opt=1#Nummer des Optimierungsdurchgangs in dem jeweiligen Strompreiszyklus
        while better==True:#solange sich die Stromkosten verkleinern werden die Phasen verkürzt
            if liste_ladephasen[Zyklus-1,0]==0 and liste_ladephasen[Zyklus-1,1]==0:
                break
           
            ladephase_neu=np.array([[liste_minima[Zyklus-1]-(ladedauer_neu/(2)),liste_minima[Zyklus-1]+(ladedauer_neu/(2))]])
            SOC_neu=get_SOC(array_names,ladephase_neu,Zyklus)
            entladedauer_neu=get_entladedauer(array_names,SOC_neu,Zyklus)
            print('SOC:',SOC_neu)
            print('entladedauer:',entladedauer_neu)
            entladephase_neu=np.array([[liste_maxima[Zyklus-1]-(entladedauer_neu/(3*3600)),liste_maxima[Zyklus-1]+(2*entladedauer_neu/(3*3600))]])# &&&
            print('ladephase die getestet wird:',ladephase_neu)
            print('entladephase die getestet wird:', entladephase_neu)
            input_laden=merge(ladephase_neu,dir_laden_daten)
            input_entladen=merge(entladephase_neu,dir_laden_daten)
        
            try:
                    #erzeuge Instanz von Dymola
                dymola = DymolaInterface()
                dymola.openModel(path=dir_modell_sim)

                dymola.translateModel(problem=name_modell_sim)
                dymola.ExecuteCommand("laden.table="+input_laden)
                dymola.ExecuteCommand("entladen.table="+input_entladen)
                result=dymola.simulateExtendedModel(problem=name_modell_sim,stopTime=simulationsdauer*3600,method='radau IIa',finalNames=['Stromkosten.y'],resultFile=os.path.join(Root_simulationsergebnisse,'optimization_test'))
                Stromkosten=result[1]
                column=np.array([ladedauer_neu,Stromkosten[0]])
                ergebnis=np.vstack((ergebnis,column))
                print('aktuelle Stromkosten',Stromkosten[0])
                if not result:
                    print("Simulation failed. Below is the translation log.")
                    log = dymola.getLastError()
                    print(log)
                
                dymola.plot(["elektrische_leistungsaufnahme.y"])
                dymola.ExportPlotAsImage(os.path.join(Root_simulationsergebnisse,"Ergebnis_von"+str(Zyklus)+str(opt)+".png"))
                
            except DymolaException as ex:
                print("Error: " + str(ex))
                
            if dymola is not None:
                dymola.close()
                dymola = None
            print('Optimierungsdurchgang der in dem Entsprechenden Strompreiszyklus durchgeführt wurde',opt)
            if opt>1:
                if ergebnis[opt,1]<ergebnis[opt-1,1]:
                    better=True
                else:
                    better=False
            else:
                better=True
            print('better:',better)
            if better==True:
                liste_ladephasen[Zyklus-1,:]=ladephase_neu
                liste_entladephasen[Zyklus-1,:]=entladephase_neu
            
            ladedauer_neu=ladedauer_neu*0.9#ladedauer wird um 10% verkürzt
            opt=opt+1
        if ergebnis[opt-2,1]>ergebnis_compare:
            print('hier_ergebnis',ergebnis)
            print('hier_ladeph',liste_ladephasen)
            print('hier_opt',opt)
            
            liste_ladephasen[Zyklus-1,:]=np.zeros((1,2))
            liste_entladephasen[Zyklus-1,:]=np.zeros((1,2))
            print('hier_ladeph',liste_ladephasen)
        Zyklus=Zyklus+1
        print('ergebnis_tabelle des  Zyklusses',ergebnis)
        #&&& hier einfügen, dass eine Lade/und Entladephase nur verwendet wird, wenn das ergebnis besser als das vergleichsergebnis ist
    return liste_ladephasen,liste_entladephasen


#simuliert das optimale Ergebnis
def simulate_optimal(ladephasen,entladephasen,simulationsdauer,dir_laden_daten,dir_modell_sim,name_modell_sim,Root_simulationsergebnisse):
    ladephasen=clear_phasen(ladephasen)
    entladephasen=clear_phasen(entladephasen)
    input_laden=merge(ladephasen,dir_laden_daten)
    input_entladen=merge(entladephasen,dir_laden_daten)
    try:
                #erzeuge Instanz von Dymola
        dymola = DymolaInterface()

        dymola.openModel(path=dir_modell_sim)

        dymola.translateModel(problem=name_modell_sim)
           
        dymola.ExecuteCommand("laden.table="+input_laden)
        dymola.ExecuteCommand("entladen.table="+input_entladen)
        result=dymola.simulateExtendedModel(problem=name_modell_sim,stopTime=simulationsdauer*3600,method='radau IIa',finalNames=['Stromkosten.y'],resultFile=os.path.join(Root_simulationsergebnisse,'simulation_optimal'))
        print(result[0])
        Stromkosten=result[1]
        print('optimale Stromkosten',Stromkosten[0])
        if not result:
            print("Simulation failed. Below is the translation log.")
            log = dymola.getLastError()
            print(log)
            
        dymola.plot(["elektrische_leistungsaufnahme.y"])
        dymola.ExportPlotAsImage(os.path.join(Root_simulationsergebnisse,"Leistungsaufnahme_optimal.png"))
        dymola.plot(["__ctt__strompreis.y[1]"])
        dymola.ExportPlotAsImage(os.path.join(Root_simulationsergebnisse,"Strompreis.png"))
        dymola.plot(["cost_calculation1.out_kkm1_drehzahl_min_unterschritten"])
        dymola.ExportPlotAsImage(os.path.join(Root_simulationsergebnisse,"Drehzahl_unterschritten.png"))
        dymola.plot(["cost_calculation1.out_Investitionskosten_kkm1"])
        dymola.ExportPlotAsImage(os.path.join(Root_simulationsergebnisse,"Invest_KKM.png"))
        dymola.plot(["cost_calculation1.out_Investitionskosten_Speicher"])
        dymola.ExportPlotAsImage(os.path.join(Root_simulationsergebnisse,"Invest_Speicher.png"))
        
    except DymolaException as ex:
        print("Error: " + str(ex))
            
    if dymola is not None:
        dymola.close()
        dymola = None
    return input_laden,input_entladen,ladephasen,entladephasen


#Simuliert das vergleichsergebnis ohne Optimierung
def simulate_compare(simulationsdauer,dir_modell_sim,name_modell_sim,Root_simulationsergebnisse):
    try:
                #erzeuge Instanz von Dymola
        dymola = DymolaInterface()

        dymola.openModel(path=dir_modell_sim)
 
        dymola.translateModel(problem=name_modell_sim)
           
        result=dymola.simulateExtendedModel(problem=name_modell_sim,stopTime=simulationsdauer*3600,method='radau IIa',finalNames=['Stromkosten.y'],resultFile=os.path.join(Root_simulationsergebnisse,'simulation_optimal'))
        print(result[0])
        Stromkosten=result[1]
            #ergebnis[step-1,1]=Stromkosten[0]☺
        print('Vergleichs-Stromkosten',Stromkosten[0])
        if not result:
            print("Simulation failed. Below is the translation log.")
            log = dymola.getLastError()
            print(log)
            
        dymola.plot(["elektrische_leistungsaufnahme.y"])
        dymola.ExportPlotAsImage(os.path.join(Root_simulationsergebnisse,"vergleichs_ergebnis.png"))
            
    except DymolaException as ex:
        print("Error: " + str(ex))
            
    if dymola is not None:
        dymola.close()
        dymola = None
    return Stromkosten


#######################################

#######################################
    
#######################################
    
#Strompreisanalyse des csv Datei wird durchgeführt
(liste_minima,liste_maxima,liste_ladephasen,simulationsdauer)=anfangsanalyse(dir_strompreis)
print(liste_ladephasen)

#Lastfall wird mithilfe des Massenstrom eingelesen und in array gespeichert
reader=csv.reader(open(dir_lastfall),delimiter=";")
last_daten=list(reader)
massenstrom=np.array(last_daten).astype("float")

#Es wird geprüft wie der Lastfall in den Be- und Entladephasen ist
(array_massenstrom_laden,array_massenstrom_entladen)=get_massenstrom(liste_minima,liste_maxima,massenstrom)

#Hier werden die entsprechenden Kennfelder simuliert und anschließend als .mat Datei abgespeichert
create_kennfeld(array_massenstrom_laden,array_massenstrom_entladen,Root_simulationsergebnisse,dir_modell_kenn,name_modell_kenn,Root_modelle,Root_kennfelder)

#der lastfall wird der csv datei entnommen und in der entsprechenden .txt datei im selben ordner wie die .mo Modell gespeichert, sodass die Tables darauf zu greifen können
#array_to_txt(massenstrom,dir_txtfile) --> wird wohl nicht benötigt

#hier wird ein array erstellt, welches die Speicherorte der Kennfelder in abhängigkeit des Strompreiszyklusses enthält, damit die optimierung die richtigen Kennfelder verwendet
array_names=create_kennfeldnamen(array_massenstrom_laden,array_massenstrom_entladen,Root_kennfelder)

#hier wird die vergleichsstrategie durchsimuliert
ergebnis_compare=simulate_compare(simulationsdauer,dir_modell_sim,name_modell_sim,Root_simulationsergebnisse)
#hier wird die Optimierung durchgeführt

(liste_ladephasen,liste_entladephasen)=optimierung(liste_minima,liste_maxima,liste_ladephasen,array_names,simulationsdauer,dir_laden_daten,dir_modell_sim,name_modell_sim,Root_simulationsergebnisse,ergebnis_compare)

#hier wird die optimale Betriebsstrategie durchsimuliert 
simulate_optimal(liste_ladephasen,liste_entladephasen,simulationsdauer,dir_laden_daten,dir_modell_sim,name_modell_sim,Root_simulationsergebnisse)

#hier wird die vergleichsstrategie durchsimuliert
simulate_compare(simulationsdauer,dir_modell_sim,name_modell_sim,Root_simulationsergebnisse)

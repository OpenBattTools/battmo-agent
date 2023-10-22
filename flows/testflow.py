from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID, uuid4
from oct2py import octave
from prefect import flow, task

class TestRequest(BaseModel):
    text: str

class ActiveMaterialClass(BaseModel):
    thickness: float
    N: Optional[int] = 10
    
class SeparatorClass(BaseModel):
    thickness: float
    N: Optional[int] = 10
    
class NegativeElectrodeClass(BaseModel):
    ActiveMaterial: ActiveMaterialClass
    
class PositiveElectrodeClass(BaseModel):
    ActiveMaterial: ActiveMaterialClass
    
class ElectrolyteClass(BaseModel):
    Separator: SeparatorClass

class Geometry1D(BaseModel):
    case: Optional[str] = "1D"
    faceArea: Optional[float] = 1e-4

class TimeSettings(BaseModel):
  totalTime: Optional[int] = 4000
  N: Optional[int] = 40
  useRampup: Optional[bool] = True
  rampupTime: Optional[int] = 10

class OutputSettings(BaseModel):
    variables: Optional[List] = ['energy', 'energyDensity', 'specificEnergy']

class Model1D(BaseModel):
    Geometry: Optional[Geometry1D] = Geometry1D()
    NegativeElectrode: Optional[NegativeElectrodeClass] = NegativeElectrodeClass(ActiveMaterial = ActiveMaterialClass(thickness = 64e-6))
    PositiveElectrode: Optional[PositiveElectrodeClass] = PositiveElectrodeClass(ActiveMaterial = ActiveMaterialClass(thickness = 57e-6))
    Electrolyte: Optional[ElectrolyteClass] = ElectrolyteClass(Separator = SeparatorClass(thickness = 15e-6))
    TimeStepping: Optional[TimeSettings] = TimeSettings()
    Output: Optional[OutputSettings] = OutputSettings()
    
class PerformanceSpec(BaseModel):
    E: Optional[float]
    energyDensity: Optional[float]
    energy: Optional[float]

class PerformanceSpecRequest(BaseModel):
    model: Optional[Model1D] = Model1D()
    uuid: UUID = Field(default_factory=uuid4, title="UUID")
    
class PerformanceSpecResponse(BaseModel):
    status: Optional[str] = "ok"
    uuid: UUID
    result: PerformanceSpec

@flow
def run_performance_spec(request: PerformanceSpecRequest):
    octave.run('/root/flows/BattMo/startupBattMo.m')
    
    print(request.model.json())
    
    battmo_input = f'/root/flows/BattMo/Examples/{str(request.uuid)}.json'
    battmo_output = f'/root/flows/BattMo/Examples/{str(request.uuid)}.json' 
    
    with open(battmo_input, "w") as f:
        f.write(request.model.json())
        
    # run the simulation
    battmo_input = f'Examples/{str(request.uuid)}.json'
    #E, energyDensity, energy = octave.runJsonFunction(func_args={"jsonfiles":{'ParameterData/BatteryCellParameters/LithiumIonBatteryCell/lithium_ion_battery_nmc_graphite.json', battmo_input}, "jsonfileoutputname": battmo_output}, nout=3)
    E, energyDensity, energy = octave.feval('runJsonFunction', {'ParameterData/BatteryCellParameters/LithiumIonBatteryCell/lithium_ion_battery_nmc_graphite.json', battmo_input}, battmo_output, True, nout=3)
    response = PerformanceSpecResponse(
        uuid=request.uuid,
        result=PerformanceSpec(E = E[:,0][-1], energyDensity = energyDensity[:,0][-1], energy = energy[:,0][-1])
    )
    return response

if __name__ == "__main__":
     run_performance_spec(request=PerformanceSpecRequest())
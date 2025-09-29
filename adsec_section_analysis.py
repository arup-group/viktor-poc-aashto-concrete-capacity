# # Load the AdSec API
# import oasys.adsec

# # Import Adsec modules 
# from Oasys.AdSec import IAdSec, ILoad, ISection, StandardMaterials, ISubComponent, IVersion
# from Oasys.AdSec.DesignCode import ACI318
# from Oasys.AdSec.IO.Graphics.Section import SectionImageBuilder
# from Oasys.AdSec.Reinforcement import IBarBundle, ICover
# from Oasys.AdSec.Reinforcement.Groups import ILinkGroup, ITemplateGroup, IPerimeterGroup
# from Oasys.AdSec.Reinforcement.Layers import ILayerByBarCount, ILayerByBarPitch
# from Oasys.AdSec.StandardMaterials import Concrete, Reinforcement
# from Oasys.Profiles import IRectangleProfile, ICatalogueProfile, IPoint
# from OasysUnits import Force, Length, Moment
# from OasysUnits.Units import ForceUnit, LengthUnit, MomentUnit

# Import other modules
import pandas as pd

# --- put this near the top of your module (remove all top-level Oasys imports) ---
_ADSEC_READY = False

def _ensure_adsec():
    global _ADSEC_READY
    if _ADSEC_READY:
        return

    import os
    if os.getenv("SKIP_ADSEC_IMPORT") == "1":
        raise RuntimeError("AdSec disabled (SKIP_ADSEC_IMPORT=1)")

    import oasys.adsec  # bootstrap CLR

    # Bind ALL the symbols you already use to module globals:
    global IAdSec, ILoad, ISection, StandardMaterials, ISubComponent, IVersion
    global ACI318, SectionImageBuilder
    global IBarBundle, ICover, ILinkGroup, ITemplateGroup, IPerimeterGroup
    global ILayerByBarCount, ILayerByBarPitch, Concrete, Reinforcement
    global IRectangleProfile, ICatalogueProfile, IPoint
    global Force, Length, Moment, ForceUnit, LengthUnit, MomentUnit

    from Oasys.AdSec import IAdSec, ILoad, ISection, StandardMaterials, ISubComponent, IVersion
    from Oasys.AdSec.DesignCode import ACI318
    from Oasys.AdSec.IO.Graphics.Section import SectionImageBuilder
    from Oasys.AdSec.Reinforcement import IBarBundle, ICover
    from Oasys.AdSec.Reinforcement.Groups import ILinkGroup, ITemplateGroup, IPerimeterGroup
    from Oasys.AdSec.Reinforcement.Layers import ILayerByBarCount, ILayerByBarPitch
    from Oasys.AdSec.StandardMaterials import Concrete, Reinforcement
    from Oasys.Profiles import IRectangleProfile, ICatalogueProfile, IPoint
    from OasysUnits import Force, Length, Moment
    from OasysUnits.Units import ForceUnit, LengthUnit, MomentUnit

    _ADSEC_READY = True

# NOT IMPLEMENTED
# Function to save interaction diagram as SVG and PNG

# Function to create a concrete section
def create_concrete_section(concrete_section, concrete_strength, cover_thickness=1.5):
    depth = Length(float(concrete_section['depth']), LengthUnit.Inch)
    width = Length(float(concrete_section['width']), LengthUnit.Inch)
    profile = IRectangleProfile.Create(depth, width)
    section = ISection.Create(profile, concrete_strength)
    section.Cover = ICover.Create(Length(float(cover_thickness), LengthUnit.Inch))
    return section

# Function to add reinforcement to a section
def add_reinforcement(section, reinforcement_bars):
    reinforcement_material = Reinforcement.Steel.ACI318.Edition_2002.US.Grade_60
    bar_perimeter = IBarBundle.Create(reinforcement_material, Length(float(reinforcement_bars["rebar_diameter"]), LengthUnit.Inch))
    bar_link = IBarBundle.Create(reinforcement_material, Length(float(reinforcement_bars["stirrup_diameter"]), LengthUnit.Inch))

    # Define perimeter reinforcement
    perimeter_group = IPerimeterGroup.Create()
    #perimeter_group.Layers.Add(ILayerByBarPitch.Create(bar_perimeter, Length(6, LengthUnit.Inch)))
    perimeter_group.Layers.Add(ILayerByBarCount.Create(int(reinforcement_bars["rebar_count"]), bar_perimeter))

    # Define link (stirrup)
    link = ILinkGroup.Create(bar_link)

    # Add defined reinforcement groups to section
    section.ReinforcementGroups.Add(link)
    section.ReinforcementGroups.Add(perimeter_group)

    return section

# Function to add steel subcomponent to a section
def add_steel_section(section, steel_section, offset_value=0):
    catalogueProfile = ICatalogueProfile.Create(steel_section)
    subComponentSection = ISection.Create(
        catalogueProfile, StandardMaterials.Steel.ASTM.A36
    )
    offset = IPoint.Create(Length.Zero, Length(float(offset_value), LengthUnit.Inch))
    encasedSubComponent = ISubComponent.Create(subComponentSection, offset)
    section.SubComponents.Add(encasedSubComponent)
    return section

# Function to perform analysis on the section
def perform_analysis(section):
    ad_sec = IAdSec.Create(ACI318.Edition_2002.US)
    solution = ad_sec.Analyse(section)
    return ad_sec, solution

# Function to check strength and calculate utilisation
def calculate_utilisation(axial, Mx, My, solution):
    load = ILoad.Create(Force(float(axial), ForceUnit.KilopoundForce), Moment(float(Mx), MomentUnit.KilopoundForceFoot), Moment(float(My), MomentUnit.KilopoundForceFoot))
    strength_result = solution.Strength.Check(load)
    utilisation = round(strength_result.LoadUtilisation.Percent, 1)
    return utilisation

# Main function to create one section and calculate utilization    
def create_composite_section(concrete_modulus, concrete_depth, concrete_width, steel_depth, steel_weight, perimeter_rebar_diameter, perimeter_rebar_count, stirrup_diameter, P_kips, Mx_kips, My_kips):

    _ensure_adsec()  # one-shot bootstrap

    conc_sec = {"depth": concrete_depth, "width": concrete_width}
    concrete_strength = {
        5000: Concrete.ACI318.Edition_2002.US.psi_5000,
        6000: Concrete.ACI318.Edition_2002.US.psi_6000,
        8000: Concrete.ACI318.Edition_2002.US.psi_8000,
        10000: Concrete.ACI318.Edition_2002.US.psi_10000
    }

    reinf_bar = {"rebar_diameter": perimeter_rebar_diameter, "rebar_count": perimeter_rebar_count, "stirrup_diameter": stirrup_diameter}
    
    # Create concrete section and add reinforcement
    section = create_concrete_section(conc_sec, concrete_strength[concrete_modulus])
    section = add_reinforcement(section, reinf_bar)

    steel_section_name = "CAT W W"+str(steel_depth)+"x"+str(steel_weight)
    section = add_steel_section(section, steel_section_name)

    # Perform analysis
    ad_sec, solution = perform_analysis(section)

    # Calculate utilisation
    utilisation = calculate_utilisation(P_kips, Mx_kips, My_kips, solution)

    # Save svg
    flattened_section = ad_sec.Flatten(section)
    svg_str = SectionImageBuilder(flattened_section).Svg()
    
    return utilisation, svg_str

if __name__ == "__main__":
    concrete_modulus = 5000
    concrete_depth = 30
    concrete_width = 30
    steel_depth = 21
    steel_weight = 132
    perimeter_rebar_diameter = 1.27
    perimeter_rebar_count = 12
    stirrup_diameter = 0.5
    P_kips = -1400
    Mx_kips = 1000
    My_kips = 1000

    actual_util, svg_str = create_composite_section(concrete_modulus, concrete_depth, concrete_width, steel_depth, steel_weight, perimeter_rebar_diameter, perimeter_rebar_count, stirrup_diameter, P_kips, Mx_kips, My_kips)
    
    print(f"Actual Utilization Ratio from Adsec: {actual_util:.4f}%")



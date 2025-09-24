
import viktor as vkt
import logging
from io import StringIO

def do_auth():
    try:
        integration = vkt.external.OAuth2Integration('azure-ad')
        access_token = integration.get_access_token()
        print(f"Access Token: {access_token}")
    except Exception as e:
        print(f"An error occurred while getting the access token: {e}")
        access_token = ""
    return access_token

# Parametrization class must be defined before Controller
class Parametrization(vkt.Parametrization):
    concrete_modulus = vkt.NumberField('Concrete Strength (psi)', default=5000, min=5000, max=10000, step=1000)
    concrete_depth = vkt.NumberField('Concrete Depth (in)', default=30)
    concrete_width = vkt.NumberField('Concrete Width (in)', default=30)
    steel_depth = vkt.NumberField('Steel Section Depth (in)', default=21)
    steel_weight = vkt.NumberField('Steel Section Weight (lb/ft)', default=132)
    perimeter_bar_diameter = vkt.NumberField('Diameter of Perimeter Bars (in)', default=1.27, min=0.01)
    perimeter_bar_num = vkt.IntegerField('Number of Perimeter Bars', default=8, min=1)
    stirrup_diameter = vkt.NumberField('Stirrup Diameter (in)', default=0.5, min=0.01)
    P_kips = vkt.NumberField('Axial Force P (kips)', default=-1400)
    Mx_kips = vkt.NumberField('Moment Mx (kip-ft)', default=1000)
    My_kips = vkt.NumberField('Moment My (kip-ft)', default=1000)

    button = vkt.SetParamsButton("Run Calc", method="run_calc")

    # Hidden fields to store state - These are mandatory
    run_counter = vkt.HiddenField("Run Counter")
    section_utilization = vkt.HiddenField("Section Utilization")
    section_svg = vkt.HiddenField("Section SVG")

class Controller(vkt.Controller):
    @vkt.ImageView("Section Image")
    def section_image(self, params, **kwargs):
        # Re-render when calc runs (or when SVG changes)
        self.viktor_view_dependencies = ["run_counter", "section_svg"]

        # If we have an SVG from the calc, show it; otherwise a tiny placeholder
        svg = params.section_svg or (
            "<svg xmlns='http://www.w3.org/2000/svg' width='400' height='200'>"
            "<rect width='100%' height='100%' fill='#f5f5f5'/>"
            "<text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle' "
            "font-family='Arial' font-size='14'>Run Calc to generate section SVG</text>"
            "</svg>"
        )
        # Return SVG as image result
        return vkt.ImageResult(StringIO(svg))
    
    parametrization = Parametrization
    logger = logging.getLogger(__name__)

    def run_calc(self, params, **kwargs):
        if hasattr(params, 'run_counter') and params.run_counter is not None:
            new_count = params.run_counter + 1
        else:
            new_count = 1

        try:
            from adsec_section_analysis import create_composite_section

            utilization, section_svg = create_composite_section(
                params.concrete_modulus,
                params.concrete_depth,
                params.concrete_width,
                params.steel_depth,
                params.steel_weight,
                params.perimeter_bar_diameter,
                params.perimeter_bar_num,
                params.stirrup_diameter,
                params.P_kips,
                params.Mx_kips,
                params.My_kips
            )
        except Exception as e:
            print(f"AdSec calculation failed: {e}")
            utilization = None
            section_svg = None

        return vkt.SetParamsResult(
            {
                'run_counter': new_count,
                'section_utilization': utilization,
                'section_svg': section_svg
            }
        )

    @vkt.DataView("Results")
    def view_results(self, params, **kwargs):
        data_group = vkt.DataGroup()

        # Show AdSec Utilization if available
        if hasattr(params, 'section_utilization') and params.section_utilization is not None:
            data_group.add(
                vkt.DataItem(
                    "Section Utilization (%)",
                    str(params.section_utilization),
                    status=vkt.DataStatus.INFO,
                    status_message="Utilization ratio computed by AdSec"
                )
            )

        # Show image tab instructions
        data_group.add(
            vkt.DataItem(
                "Section Image",
                "Go to the 'Section Image' tab to view the generated section image.",
                status=vkt.DataStatus.INFO,
                status_message="The image is generated and available in the Section Image tab."
            )
        )

        return vkt.DataResult(data_group)

    @vkt.WebView('Report')
    def html_report(self, params, **kwargs):
        html_report = '<html>No report available, run the calculation first.</html>'
        return vkt.WebResult(html=html_report)
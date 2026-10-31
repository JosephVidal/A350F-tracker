from pprint import pprint

from a350f_tracker.providers.adsbx import AdsbFiProvider

provider = AdsbFiProvider()
observations = provider.get_by_registration("F-WXLD")

for observation in observations:
    pprint(observation.model_dump())

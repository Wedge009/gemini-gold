import dj_lib
import trading
import universe
def run():
  dj_lib.disable()
  trading.rerollBaseCargo(universe.getDockedBase())

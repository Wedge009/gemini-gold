"""Work-arounds for engine behaviour the scripts can't otherwise rely on.

Imported for its side effects, before anything else, by privateer.py (which
every game mission loads).
"""
import VS

# The engine gives VS.Unit only Python 2's __nonzero__, which Python 3 ignores,
# so a null unit counts as true and every "if un:" or "if not un:" test goes
# the wrong way. Random encounters, for one, never see the player near a base.
# Add the Python 3 hook until the engine defines it itself.
if '__bool__' not in VS.Unit.__dict__:
    try:
        VS.Unit.__bool__ = lambda self: not self.isNull()
    except (AttributeError, TypeError) as e:
        print('engine_compat: could not add VS.Unit.__bool__: %s' % e)

"""Shared model guidance, not a runtime permission or proof of UI correctness."""

UI_INTERACTION_CONTRACT = '''UI INTERACTION CONTRACT v1 (within the agreed scope):
Plan a first-time visitor journey: goal, orientation, expected action/result,
feedback and return; avoid dead ends and hidden gestures. In notes map each
control's selector to trigger, state, return, keyboard/touch and test case.
Menu button: click/Enter/Space opens options, updates aria-expanded; Escape,
Close/backdrop closes and restores focus. No zoom.
Navigation link: named view. Media card: preview.
Scroll scene: native scroll drives position/scale locally, never globally hijacks
wheel/Ctrl+wheel. Explicit preview zoom: plus/minus/reset, preserve browser pinch.
Video: native controls and page scroll; time scrubbing only if explicitly asked,
with normal playback fallback.
Back: close top overlay first, else prior in-app view, preserve form data.
Empty-background Back only where specified; exclude controls, selection, drags.
No parent escape. Decorations: pointer-events:none, aria-hidden, no obscured UI.
Keep tasks accessible with reduced motion and small screens. Add no unrequested
features. Require independent browser tests; never claim they passed yourself.
'''

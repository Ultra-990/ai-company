"""Regression: native wheel must render photos before iframe keyboard focus."""
import asyncio
import json
import os
from pathlib import Path

import pytest

from tests.browser_multifile_probe import check
from scripts.studio_bundle import read_bundle, frame_content
from scripts.compare_local_models import check_idle


@pytest.mark.skipif(not os.environ.get('AIC_STUDIO_BUNDLE'), reason='Explicit synthetic bundle browser check')
def test_scroll_photos_without_clicking_or_forcing_iframe_focus(client):
    check_idle()
    files, _, _ = read_bundle(Path(os.environ['AIC_STUDIO_BUNDLE']))
    html, frontend = frame_content(files)
    async def inspect(evaluate, context, call, session):
        async def js(expression): return await evaluate(expression, context)
        await call('Emulation.setDeviceMetricsOverride', {'width':1440, 'height':1000,
            'deviceScaleFactor':1, 'mobile':False}, session)
        await asyncio.sleep(.2)
        initial = await js("({focused:document.hasFocus(),hidden:document.hidden,position:document.querySelector('#visuals').dataset.scenePosition})")
        print('Initial scroll state:', json.dumps(initial))
        assert initial['hidden'] is False
        assert initial['focused'] is False, 'Do not give the frame keyboard focus before testing wheel'
        assert initial.get('position') is not None, 'Lay out photos before the first click'
        await js("window.probeFocusCalls=0;window.probeNativeFocus=HTMLElement.prototype.focus;HTMLElement.prototype.focus=function(...args){window.probeFocusCalls++;return window.probeNativeFocus.apply(this,args)}")
        # Wheel from the top of the actual document, no click or focus()/scrollTo().
        target = await js("scrollY+document.querySelector('.scene-journey').getBoundingClientRect().top+800")
        await call('Input.dispatchMouseEvent', {'type':'mouseMoved','x':720,'y':450}, session)
        await call('Input.dispatchMouseEvent', {'type':'mouseWheel','x':720,'y':450,'deltaX':0,'deltaY':target}, session)
        await asyncio.sleep(1)
        result = await js("({focused:document.hasFocus(),scroll:scrollY,position:Number(document.querySelector('#visuals').dataset.scenePosition),transforms:[...document.querySelectorAll('[data-art]')].map(e=>getComputedStyle(e).transform),focusCalls:window.probeFocusCalls})")
        print('After wheel:', json.dumps(result))
        assert result['scroll'] > 0
        assert result['position'] is not None and result['position'] > .25, 'Visible scene did not follow native wheel before focus'
        assert result['focusCalls'] == 0 and result['focused'] is False
        assert len(set(result['transforms'])) == 3, 'Photos must occupy distinct spatial positions'
        await call('Input.dispatchMouseEvent', {'type':'mouseWheel','x':720,'y':450,'deltaX':0,'deltaY':-700}, session)
        await asyncio.sleep(.8)
        assert await js("Number(document.querySelector('#visuals').dataset.scenePosition)") < result['position']
        assert await js('window.probeFocusCalls') == 0
        # Hidden documents still stop painting. Focus guards remain independent.
        await js("Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))")
        frozen = await js("document.querySelector('#visuals').dataset.scenePosition")
        await js("scrollBy(0,300);window.dispatchEvent(new Event('scroll'))")
        await asyncio.sleep(.15)
        assert await js("document.querySelector('#visuals').dataset.scenePosition") == frozen
        assert await js("window.StudioFocus.focus(document.querySelector('#main'))") is False
        assert await js('window.probeFocusCalls') == 0
        await js("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))")
        await js('HTMLElement.prototype.focus=window.probeNativeFocus')
    asyncio.run(check(client, {}, {}, cases=[], expected_color=None,
        preview_request=lambda path: {'response': {'body': html}, 'assets': frontend},
        before_activation=inspect))

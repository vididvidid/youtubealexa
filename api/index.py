import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

if os.environ.get("YTA_HOME") in [None, ""]:
    os.environ["YTA_HOME"] = "/tmp/ytalexa"

import alexa
import audio as au
import cfg
import http_core as hc
import log
import routes_ui

cfg.cfg_init()
au.au_init(os.environ["YTA_HOME"])
routes_ui.ui_init(ROOT)
routes_ui.ui_routes()
alexa.ax_routes()
log.LOG_ECHO = 1

handler = hc.HttpH

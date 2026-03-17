#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批次1：全球、台灣、中國、香港、澳門、韓國、日本"""
import subprocess
import sys
subprocess.run([sys.executable, 'fetch_statcounter_all_platforms.py', 'batch1'])

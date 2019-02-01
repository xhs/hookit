#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import os

PEEK_BUFFER_SIZE = os.getenv('PEEK_BUFFER_SIZE', 128)
RELAY_BUFFER_SIZE = os.getenv('PROXY_BUFFER_SIZE', 1024 * 512)

task_queue_size = os.getenv('TASK_QUEUE_SIZE')
TASK_QUEUE_SIZE = int(task_queue_size) if task_queue_size else math.inf

__all__ = ['PEEK_BUFFER_SIZE', 'RELAY_BUFFER_SIZE', 'TASK_QUEUE_SIZE']

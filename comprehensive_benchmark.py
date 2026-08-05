#!/usr/bin/env python3
"""
Comprehensive benchmark suite for all Hermes AI task types.
Tests vision, text completion, and web search across all available models.
Reports timing, token throughput, quality metrics, and best configurations.
"""
import requests, time, json, sys, os, subprocess
from datetime import datetime
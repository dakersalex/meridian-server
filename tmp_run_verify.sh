#!/bin/bash
nohup python3 ~/meridian-server/tmp_eco_verify.py > ~/meridian-server/tmp_eco_verify_out.txt 2>&1
echo "DONE" >> ~/meridian-server/tmp_eco_verify_out.txt

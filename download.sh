#!/bin/bash
if [ ! -f ./test/allthethings.json ]; then
    wget https://secure.pub.build.mozilla.org/builddata/reports/allthethings/allthethings.20160516060001._87b285bcdaf0_21165e565d41_186a28cf7485.json -O ./test/fixtures/allthethings.json
fi
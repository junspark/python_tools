#!/bin/bash

echo `ls -l $1 | awk ' {print $5}'`


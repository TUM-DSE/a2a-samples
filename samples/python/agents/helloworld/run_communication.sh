#!/bin/bash

print_help(){
	echo "Usage: $0 <VM/CVM/Vanilla/Guardian> [base_url]"
	exit 0
}

if [ $# -lt 1 ]; then
	print_help
fi

base_url=''
if [ $1 = "VM" ] || [ $1 = "CVM" ]; then
	cd ../../../agents/a2a-samples/samples/python/agents/helloworld
	base_url='http://192.168.32.10:9999'
fi

if [ $# = 2 ]; then
	base_url=$2
	echo $base_url
fi

source .venv/bin/activate || exit

for i in $(seq 500 500 10000)
do
	python3 test_client.py $i $base_url
done



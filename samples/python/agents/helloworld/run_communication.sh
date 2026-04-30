#!/bin/bash

print_help(){
	echo "Usage: $0 <VM/CVM/Vanilla> [base_url]"
	exit 0
}

if [ $# -lt 1 ]; then
	print_help
fi

base_url=''
if [ $1 = "VM" ] || [ $1 = "CVM" ]; then
	#cd ../../../agents/a2a-samples/samples/python/agents/helloworld
	base_url='http://192.168.32.10:9999'
fi

if [ $# = 2 ]; then
	base_url=$2
	echo $base_url
fi

source .venv/bin/activate || exit

sizes=(64 256 1024 $((8 * 1024)) $((16 * 1024)) $((64 * 1024)) $((256 * 1024)) $((1024 * 1024)))


for i in ${sizes[@]};
do
	python3 test_client.py $i $base_url
done



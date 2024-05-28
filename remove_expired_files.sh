#!/bin/bash
cd /home/user/DB_DUMPS
tail=".sql.gz"
timestamp=$(date --date="30 days ago" -I'date')
echo ${timestamp}
for file in *${tail}
do
  datepart=${file:0:10}
  if [[ ${datepart} < ${timestamp} ]]
  then rm "${file}"
  fi
done

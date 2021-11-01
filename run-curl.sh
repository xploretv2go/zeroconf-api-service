CURL='/usr/bin/curl'
RVMHTTP="http://localzeroconf:15051/a1/xploretv/v1/zeroconf"
CURLARGS="-X GET"


raw="$($CURL $CURLARGS $RVMHTTP)"
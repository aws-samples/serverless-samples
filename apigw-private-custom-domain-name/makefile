include etc/environment.sh

cert: cert.package cert.deploy
cert.package:
	sam package -t ${CERT_TEMPLATE} --output-template-file ${CERT_OUTPUT} --s3-bucket ${S3BUCKET}
cert.deploy:
	sam deploy -t ${CERT_OUTPUT} --stack-name ${CERT_STACK} --parameter-overrides ${CERT_PARAMS} --capabilities CAPABILITY_NAMED_IAM

apigw: apigw.package apigw.deploy
apigw.package:
	sam package -t ${APIGW_TEMPLATE} --output-template-file ${APIGW_OUTPUT} --s3-bucket ${S3BUCKET}
apigw.deploy:
	sam deploy -t ${APIGW_OUTPUT} --stack-name ${APIGW_STACK} --parameter-overrides ${APIGW_PARAMS} --capabilities CAPABILITY_NAMED_IAM

nlb: nlb.package nlb.deploy
nlb.package:
	sam package -t ${NLB_TEMPLATE} --output-template-file ${NLB_OUTPUT} --s3-bucket ${S3BUCKET}
nlb.deploy:
	sam deploy -t ${NLB_OUTPUT} --stack-name ${NLB_STACK} --parameter-overrides ${NLB_PARAMS} --capabilities CAPABILITY_NAMED_IAM

alb: alb.package alb.deploy
alb.package:
	sam package -t ${ALB_TEMPLATE} --output-template-file ${ALB_OUTPUT} --s3-bucket ${S3BUCKET}
alb.deploy:
	sam deploy -t ${ALB_OUTPUT} --stack-name ${ALB_STACK} --parameter-overrides ${ALB_PARAMS} --capabilities CAPABILITY_NAMED_IAM

r53: r53.package r53.deploy
r53.package:
	sam package -t ${R53_TEMPLATE} --output-template-file ${R53_OUTPUT} --s3-bucket ${S3BUCKET}
r53.deploy:
	sam deploy -t ${R53_OUTPUT} --stack-name ${R53_STACK} --parameter-overrides ${R53_PARAMS} --capabilities CAPABILITY_NAMED_IAM

alt.cert: alt.cert.package alt.cert.deploy
alt.cert.package:
	sam package -t ${ALT_CERT_TEMPLATE} --output-template-file ${ALT_CERT_OUTPUT} --s3-bucket ${S3BUCKET}
alt.cert.deploy:
	sam deploy -t ${ALT_CERT_OUTPUT} --stack-name ${ALT_CERT_STACK} --parameter-overrides ${ALT_CERT_PARAMS} --capabilities CAPABILITY_NAMED_IAM

alt.apigw: alt.apigw.package alt.apigw.deploy
alt.apigw.package:
	sam package -t ${ALT_APIGW_TEMPLATE} --output-template-file ${ALT_APIGW_OUTPUT} --s3-bucket ${S3BUCKET}
alt.apigw.deploy:
	sam deploy -t ${ALT_APIGW_OUTPUT} --stack-name ${ALT_APIGW_STACK} --parameter-overrides ${ALT_APIGW_PARAMS} --capabilities CAPABILITY_NAMED_IAM

alt.nlb: alt.nlb.package alt.nlb.deploy
alt.nlb.package:
	sam package -t ${ALT_NLB_TEMPLATE} --output-template-file ${ALT_NLB_OUTPUT} --s3-bucket ${S3BUCKET}
alt.nlb.deploy:
	sam deploy -t ${ALT_NLB_OUTPUT} --stack-name ${ALT_NLB_STACK} --parameter-overrides ${ALT_NLB_PARAMS} --capabilities CAPABILITY_NAMED_IAM

alt.alb: alt.alb.package alt.alb.deploy
alt.alb.package:
	sam package -t ${ALT_ALB_TEMPLATE} --output-template-file ${ALT_ALB_OUTPUT} --s3-bucket ${S3BUCKET}
alt.alb.deploy:
	sam deploy -t ${ALT_ALB_OUTPUT} --stack-name ${ALT_ALB_STACK} --parameter-overrides ${ALT_ALB_PARAMS} --capabilities CAPABILITY_NAMED_IAM

alt.r53: alt.r53.package alt.r53.deploy
alt.r53.package:
	sam package -t ${ALT_R53_TEMPLATE} --output-template-file ${ALT_R53_OUTPUT} --s3-bucket ${S3BUCKET}
alt.r53.deploy:
	sam deploy -t ${ALT_R53_OUTPUT} --stack-name ${ALT_R53_STACK} --parameter-overrides ${ALT_R53_PARAMS} --capabilities CAPABILITY_NAMED_IAM

lambda.local:
	sam local invoke -t ${LAMBDA_TEMPLATE} --parameter-overrides ${LAMBDA_PARAMS} --env-vars etc/envvars.json -e etc/event.json Fn | jq
lambda.invoke.sync:
	aws --profile ${PROFILE} lambda invoke --function-name ${O_FN} --invocation-type RequestResponse --payload file://etc/event.json --cli-binary-format raw-in-base64-out --log-type Tail tmp/fn.json | jq "." > tmp/response.json
	cat tmp/response.json | jq -r ".LogResult" | base64 --decode
	cat tmp/fn.json | jq
lambda.invoke.async:
	aws --profile ${PROFILE} lambda invoke --function-name ${O_FN} --invocation-type Event --payload file://etc/event.json --cli-binary-format raw-in-base64-out --log-type Tail tmp/fn.json | jq "."

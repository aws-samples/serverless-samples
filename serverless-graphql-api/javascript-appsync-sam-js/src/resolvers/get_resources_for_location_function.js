import { util } from '@aws-appsync/utils';

export function request(ctx) {
  var exp = null;
  var locationid={};
  if (ctx.args.locationid) {exp = ctx.args.locationid} 
    else {if (ctx.source.locationid) {exp = ctx.source.locationid} 
      else {if (ctx.stash.locationid) {exp=ctx.stash.locationid}}
  }
  if (exp) {
    locationid = { ":locationid": exp }
  } else {
    util.error('Location ID missing in the request')
  }
  return {
    operation: 'Query',
    query: {
      expression: "locationid = :locationid",
      expressionValues: util.dynamodb.toMapValues(locationid)
    },
    index: "locationidGSI"
  }
}

export function response(ctx) {
  const { error, result } = ctx;
  if (error) {
    return util.appendError(error.message, error.type, result);
  }
  return ctx.result.items;
}

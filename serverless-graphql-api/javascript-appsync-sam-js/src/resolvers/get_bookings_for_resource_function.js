import { util } from '@aws-appsync/utils';

export function request(ctx) {
  var exp = null;
  var resourceid={};
  if (ctx.args.resourceid) {exp = ctx.args.resourceid} 
    else {if (ctx.source.resourceid) {exp = ctx.source.resourceid} 
      else {if (ctx.stash.resourceid) {exp= ctx.stash.resourceid}}
  }
  if (exp) {
    resourceid = { ":resourceid": exp }
  } else {
    util.error('Resource ID missing in the request')
  }
  return {
    operation: 'Query',
    query: {
      expression: "resourceid = :resourceid",
      expressionValues: util.dynamodb.toMapValues(resourceid)
    },
    index: "bookingsByResourceByTimeGSI"
  }
}

export function response(ctx) {
  const { error, result } = ctx;
  if (error) {
    return util.appendError(error.message, error.type, result);
  }
  return ctx.result.items;
}

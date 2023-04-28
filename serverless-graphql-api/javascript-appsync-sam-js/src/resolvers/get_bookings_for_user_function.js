import { util } from '@aws-appsync/utils';

export function request(ctx) {
  const userid = { ":userid": ctx.identity.sub }
  return {
    operation: 'Query',
    query: {
      expression: "userid = :userid",
      expressionValues: util.dynamodb.toMapValues(userid)
    },
    index: "useridGSI"
  }
}

export function response(ctx) {
  const { error, result } = ctx;
  if (error) {
    return util.appendError(error.message, error.type, result);
  }
  return ctx.result.items;
}

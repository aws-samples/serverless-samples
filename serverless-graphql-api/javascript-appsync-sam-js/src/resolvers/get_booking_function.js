import { util } from '@aws-appsync/utils';

export function request(ctx) {
  const key = { bookingid: ctx.args.bookingid }
  return {
    operation: 'GetItem',
    key: util.dynamodb.toMapValues(key),
  };
}

export function response(ctx) {
  const { error, result } = ctx;
  if (error) {
    return util.appendError(error.message, error.type, result);
  }
  return ctx.result;
}


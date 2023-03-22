import { util } from '@aws-appsync/utils';

export function request(ctx) {
    const values = ctx.args;
    var key = { bookingid: util.autoId() };
    if (ctx.args.bookingid) {
        key = { bookingid: ctx.args.bookingid };
        delete values.bookingid; 
    }
    values.timestamp = util.time.nowISO8601();
    values.userid =  ctx.identity.sub;
    return {
        operation: 'PutItem',
        key: util.dynamodb.toMapValues(key),
        attributeValues: util.dynamodb.toMapValues(values)
    }
  }

  export function response(ctx) {
    const { error, result } = ctx;
    if (error) {
      return util.appendError(error.message, error.type, result);
    }
    return ctx.result;
  }
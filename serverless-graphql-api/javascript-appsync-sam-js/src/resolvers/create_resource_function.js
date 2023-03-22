import { util } from '@aws-appsync/utils';

export function request(ctx) {
    const values = ctx.args;
    var key = { resourceid: util.autoId() };
    if (ctx.args.resourceid) {
        key = { resourceid: ctx.args.resourceid };
        delete values.resourceid; 
    }
    values.timestamp = util.time.nowISO8601();
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
import { util } from '@aws-appsync/utils';

export function request(ctx) {
    const UserPoolAdminGroupName = "apiAdmins";
    var isAdmin = false;
    const key = { bookingid: ctx.args.bookingid }
    const userid = { ":userid": ctx.identity.sub }
    if (ctx.identity.claims["cognito:groups"]) {
        for (var group in ctx.identity.claims["cognito:groups"]) {
            if (ctx.identity.claims["cognito:groups"][group] == UserPoolAdminGroupName) {
                isAdmin = true;
            }
        }
    }
    var response = {
        operation: 'DeleteItem',
        key: util.dynamodb.toMapValues(key),
    }
    if (!isAdmin) {
        response.condition = {
            expression: "userid = :userid",
            expressionValues: util.dynamodb.toMapValues(userid)
        }
    }
    return response
}

export function response(ctx) {
    const { error, result } = ctx;
    if (error) {
        if (error.type=="DynamoDB:ConditionalCheckFailedException") {
            return util.appendError("User is not authorized to perform this action.", "Unauthorized", null)
        } else {
            return util.appendError(error.message, error.type, result);
        }
    }
    return ctx.args.bookingid;
}


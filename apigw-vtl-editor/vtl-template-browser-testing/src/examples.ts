export interface Example {
  name: string;
  inputJson: string;
  template: string;
  expectedOutput: string;
}

export const examples: Example[] = [
  {
    name: 'Simple Greeting',
    inputJson: `{
  "name": "John",
  "age": 30
}`,
    template: `{
  "greeting": "Hello, $name!",
  "userAge": $age
}`,
    expectedOutput: `{
  "greeting": "Hello, John!",
  "userAge": 30
}`
  },
  {
    name: 'Conditional Logic',
    inputJson: `{
  "name": "Alice",
  "age": 17,
  "country": "USA"
}`,
    template: `{
  "greeting": "Hello, $name!",
  #if($age >= 18)
  "message": "You are an adult.",
  #else
  "message": "You are a minor.",
  #end
  "location": "$country"
}`,
    expectedOutput: `{
  "greeting": "Hello, Alice!",
  "message": "You are a minor.",
  "location": "USA"
}`
  },
  {
    name: 'Looping',
    inputJson: `{
  "items": [
    {"name": "Apple", "price": 1.20},
    {"name": "Banana", "price": 0.50},
    {"name": "Orange", "price": 0.75}
  ]
}`,
    template: `{
  "products": [
    #foreach($item in $items)
    {
      "productName": "$item.name",
      "productPrice": $item.price,
      "discountPrice": $math.roundTo(2, $item.price * 0.9)
    }#if($foreach.hasNext),#end
    #end
  ]
}`,
    expectedOutput: `{
  "products": [
    {
      "productName": "Apple",
      "productPrice": 1.2,
      "discountPrice": 1.08
    },
    {
      "productName": "Banana",
      "productPrice": 0.5,
      "discountPrice": 0.45
    },
    {
      "productName": "Orange",
      "productPrice": 0.75,
      "discountPrice": 0.68
    }
  ]
}`
  },
  {
    name: 'Advanced Features',
    inputJson: `{
  "user": {
    "firstName": "Jane",
    "lastName": "Doe",
    "roles": ["admin", "editor"],
    "settings": {
      "theme": "dark",
      "notifications": true
    }
  },
  "currentDate": "2023-05-15"
}`,
    template: `{
  "fullName": "$user.firstName $user.lastName",
  "isAdmin": #if($user.roles.contains("admin"))true#{else}false#end,
  "roleCount": $user.roles.size(),
  "preferences": {
    "darkMode": #if($user.settings.theme == "dark")true#{else}false#end,
    "notificationsEnabled": $user.settings.notifications
  },
  "formattedDate": "$date.format('yyyy-MM-dd', $currentDate)"
}`,
    expectedOutput: `{
  "fullName": "Jane Doe",
  "isAdmin": true,
  "roleCount": 2,
  "preferences": {
    "darkMode": true,
    "notificationsEnabled": true
  },
  "formattedDate": "2023-05-15"
}`
  }
];

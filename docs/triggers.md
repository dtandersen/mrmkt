## Triggers

### Create a trigger

Create a trigger. If no trigger name is specified it defaults to `trigger-######`.

`mrmkt trigger create [<trigger>]`

- --symbol <symbol>
- --signal <signal>
- --operator <operator>
- --value <value>
- --frequency <frequency>
- --expires <date>
- --message <str>

### List triggers

List all triggers.

`mrmkt trigger list`

### Show trigger

Show a trigger

`mrmkt trigger show <trigger`

### Delete a trigger

Delete a trigger. It is also removed from any trigger sets.

`mrmkt trigger remove <trigger>`

## Trigger Sets

### Create a trigger set

`mrmkt triggerset create`

- --name <name> (optional)

### Add a trigger to a trigger set

`mrmkt triggerset add <triggerset> <trigger>`

### Remove a trigger from a trigger set

`mrmkt triggerset remove <triggerset> <trigger>`

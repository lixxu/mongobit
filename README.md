mongobit
========
Simple Mongo ORM

## Version 0.3 changes
add support pymongo >= 3.0

## Important Notice
Version 0.2 is <b>not compitable</b> with version 0.1.
Please update your script before upgrading to 0.2.

The major change is the paramaters in save, update functions,
and version 0.2 support more update operators, such as:

* $set - Use the $set operator to set a particular value
* $unset - The $unset operator deletes a particular field
* $inc - The $inc operator increments a value of a field by a specified amount
* $push - The $push operator appends a specified value to an array
* $pull - The $pull operator removes all instances of a value from an existing array
* $pullAll - The $pullAll operator removes multiple values from an existing array
* $pop - The $pop operator removes the first or last element of an array
* $addToSet - The $addToSet operator adds a value to an array only if the value is not in the array already

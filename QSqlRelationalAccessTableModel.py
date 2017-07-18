from PyQt4.QtSql import *


# Reimplementation of the selectStatement for use with Access databases
# since the standard method creates Access incompatible SQL statements on LEFT JOIN
class QSqlRelationalAccessTableModel(QSqlRelationalTableModel):

    joinMode = QSqlRelationalTableModel.InnerJoin
    relations = {}

    def selectStatement(self):
        query = ''

        if not self.tableName():
            return query
        if not self.relations:
            return QSqlRelationalTableModel.selectStatement(self)

        tList = ''
        fList = ''
        where = ''

        driver = self.database().driver()
        rec = self.record()
        tables = []

        # Count how many times each field name occurs in the record
        fieldNames = {}
        fieldList = []
        for idx in range(rec.count()):
            relation = self.relation(idx)
            if relation.isValid():
                name = relation.displayColumn()
                if driver.isIdentifierEscaped(name, QSqlDriver.FieldName):
                    name = driver.stripDelimiters(name, QSqlDriver.FieldName)

                relRec = self.database().record(relation.tableName())
                for i in range(relRec.count()):
                    if name.lower() == relRec.fieldName(i).lower():
                        name = relRec.fieldName(i)
                        break
            else:
                name = rec.fieldName(idx)
            fieldNames[name] = fieldNames.get(name, 0) + 1
            fieldList.append(name)

        for idx in range(rec.count()):
            relation = self.relation(idx)
            if relation.isValid():
                relTableAlias = 'relTblAl_%d' % idx
                if len(fList):
                    fList += ', '
                fList += relTableAlias + '.' + relation.displayColumn()

                # If there are duplicate field names they must be aliased
                if fieldNames[fieldList[idx]] > 1:
                    relTableName = relation.tableName().rsplit('.', 1)[0]
                    if driver.isIdentifierEscaped(relTableName, QSqlDriver.TableName):
                        relTableName = driver.stripDelimiters(relTableName, QSqlDriver.TableName)
                    displayColumn = relation.displayColumn()
                    if driver.isIdentifierEscaped(displayColumn, QSqlDriver.FieldName):
                        displayColumn = driver.stripDelimiters(displayColumn, QSqlDriver.FieldName)
                    fList += ' AS %s_%s_%s' % (relTableName, displayColumn, fieldNames[fieldList[idx]])
                    fieldNames[fieldList[idx]] -= 1

                if self.joinMode == QSqlRelationalTableModel.InnerJoin:
                    # Original Qt comment:
                    # this needs fixing!! the below if is borken.
                    # Use LeftJoin mode if you want correct behavior
                    tables.append(relation.tableName() + ' ' + relTableAlias)
                    if where:
                        where += ' AND '
                    where += self.tableName() + '.' + driver.escapeIdentifier(rec.fieldName(idx), QSqlDriver.FieldName)
                    where += ' = ' + relTableAlias + '.' + relation.indexColumn() + ')'
                else:
                    tables.append(' LEFT JOIN')
                    tables.append(relation.tableName() + ' ' + relTableAlias)
                    tables.append('ON')
                    clause = self.tableName() + '.' + driver.escapeIdentifier(rec.fieldName(idx), QSqlDriver.FieldName)
                    clause += ' = ' + relTableAlias + '.' + relation.indexColumn() + ')'
                    tables.append(clause)
            else:
                if len(fList):
                    fList += ', '
                fList += self.tableName() + '.' + driver.escapeIdentifier(rec.fieldName(idx), QSqlDriver.FieldName)

        if self.joinMode == QSqlRelationalTableModel.InnerJoin and len(tables):
            tList += ', '.join(tables)
            if len(tList):
                tList = ', ' + tList
        else:
            # left join!
            tList += ' '.join(tables)

        if not len(fList):
            return query

        # Assemble query parts
        tList = self.tableName() + tList
        if self.joinMode == QSqlRelationalTableModel.LeftJoin:
            tList = '(' * len(self.relations) + tList
        query = 'SELECT ' + fList + ' FROM ' + tList

        if self.joinMode == QSqlRelationalTableModel.InnerJoin:
            query = self.qAppendWhereClause(query, where, self.filter())
        else:
            # left join!
            if self.filter():
                query += ' WHERE (' + self.filter() + ')'

        if self.orderByClause():
            query += ' ' + self.orderByClause()

        return query

    # Make joinmode accessible
    def setJoinMode(self, joinMode):
        self.joinMode = joinMode
        QSqlRelationalTableModel.setJoinMode(self, joinMode)

    # Keep track of relations
    def setRelation(self, column, relation):
        if relation.isValid():
            self.relations[column] = relation
        else:
            if column in self.relations:
                del self.relations[column]

        QSqlRelationalTableModel.setRelation(self, column, relation)

    def qAppendWhereClause(self, query, clause1, clause2):
        if not len(clause1) and not len(clause2):
            return
        if not len(clause1) or not len(clause2):
            query += ' WHERE (' + clause1 + clause2 + ')'
        else:
            query += ' WHERE (' + clause1 + ') AND (' + clause2 + ') '

        return query

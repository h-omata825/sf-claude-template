```apex
@isTest
private class AccountServiceTest {

    @TestSetup
    static void setup() {
        // テストデータは @TestSetup で一元管理
        insert new Account(Name = 'Test Account', Industry = 'Technology');
    }

    @isTest
    static void testNormalCase() {
        Account acc = [SELECT Id FROM Account LIMIT 1];
        Test.startTest();
        AccountService.activate(acc.Id);
        Test.stopTest();
        Account result = [SELECT Status__c FROM Account WHERE Id = :acc.Id];
        System.assertEquals('Active', result.Status__c, '正常ケース: ステータスがActiveになること');
    }

    @isTest
    static void testBulkCase() {
        // バルクテスト: 200件以上で検証
        List<Account> bulk = new List<Account>();
        for (Integer i = 0; i < 200; i++) {
            bulk.add(new Account(Name = 'Bulk ' + i));
        }
        insert bulk;
        Test.startTest();
        AccountService.activateBulk(bulk);
        Test.stopTest();
        System.assertEquals(200, [SELECT COUNT() FROM Account WHERE Status__c = 'Active' AND Name LIKE 'Bulk%']);
    }

    @isTest
    static void testErrorCase() {
        try {
            AccountService.activate(null);
            System.assert(false, '例外が発生するはずが発生しなかった');
        } catch (AccountService.ServiceException e) {
            System.assert(e.getMessage().contains('必須'), '期待するエラーメッセージであること');
        }
    }
}
```

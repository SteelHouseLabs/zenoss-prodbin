def test_suite():
    from Products import ZenRelations as product
    from Products.ZenTestRunner import getTestSuites
    return getTestSuites(product)

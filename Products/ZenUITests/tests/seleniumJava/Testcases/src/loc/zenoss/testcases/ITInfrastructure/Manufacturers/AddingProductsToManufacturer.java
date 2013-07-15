/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.ITInfrastructure.Manufacturers;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import loc.zenoss.Common;
import loc.zenoss.Manufacturers;
import loc.zenoss.ZenossConstants;
import loc.zenoss.TestlinkXMLRPC;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class AddingProductsToManufacturer {
	private static int testCaseID = 2129;
	private static String testCaseResult = "f"; //Fail by default

	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;

	@BeforeClass
	public static void setUpBeforeClass() throws Exception {
		selenese = new SeleneseTestCase();  
		sClient = new DefaultSelenium(ZenossConstants.SeleniumHubHostname, 4444,
				ZenossConstants.browser, ZenossConstants.testedMachine)  {
			public void open(String url) {
				commandProcessor.doCommand("open", new String[] {url,"true"});
			}     	};
			sClient.start();
			sClient.deleteAllVisibleCookies();
	}

	@AfterClass
	public static void tearDownAfterClass() throws Exception {
		sClient.stop();
		TestlinkXMLRPC.UpdateTestCaseResult(testCaseID, ZenossConstants.testPlanID, testCaseResult);
	}

	@Before
	public void setUp() throws Exception {

	}

	@After
	public void tearDown() throws Exception {
	}

	@Test
	public void addingProductsToManufacturer() throws Exception{
		String manufacturer = "testProducts";
		String url = "testURL.com";
		String address1 = "testAddress";
		String city = "San Jose";
		String country = "Costa Rica";
		String state= "San Jose";
		String zip = "00000";
		String hardware = "testHardware";
		String software = "testSoftware";
		String os = "testOS"; 

		Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);

		//Click Infrastructure
		sClient.click("link=Infrastructure");
		Thread.sleep(8000);

		// Click on Manufacturers
		sClient.click("link=Manufacturers");
		sClient.waitForPageToLoad("30000");

		//Create new manufacturer
		Manufacturers.createManufacturers(sClient, manufacturer);

		// Click on the manufacturer
		sClient.click("//tbody[@id='Manufacturers']/tr/td/a[text()='"+manufacturer+"']");
		// Click on Edit button
		Thread.sleep(5000);
		sClient.click("link=Edit");
		sClient.waitForPageToLoad("30000");
		// Add URL
		Thread.sleep(2000);
		sClient.type("url", url);
		sClient.type("address1",address1 );
		sClient.type("city", city);
		sClient.type("country", country);
		sClient.type("state", state);
		sClient.type("zip",zip);
		Thread.sleep(2000);
		// Click on Save button
		sClient.click("//input[@value=' Save ']");
		Thread.sleep(4000);
		selenese.verifyTrue(sClient.isTextPresent("Saved at time:"));
		// Click on Overview
		sClient.click("link=Overview");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(4000);
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Manufacturer']/tr/td[text()='"+manufacturer+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Manufacturer']/tr/td/a[text()='"+url+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Manufacturer']/tr/td[text()='"+address1+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Manufacturer']/tr/td[text()='"+state+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Manufacturer']/tr/td[text()='"+country+"']"));
		selenese.verifyTrue(sClient.isElementPresent("//tbody[@id='Manufacturer']/tr/td[text()='"+zip+"']"));

		//Add new Hardware
		Manufacturers.addNewHarware(sClient, hardware);
		Thread.sleep(2000);

		//Add new Software
		Manufacturers.addNewSoftware(sClient, software);
		Thread.sleep(2000);

		//Add new Operating System
		Manufacturers.addNewOS(sClient, os);

		testCaseResult = "p";
	}
}

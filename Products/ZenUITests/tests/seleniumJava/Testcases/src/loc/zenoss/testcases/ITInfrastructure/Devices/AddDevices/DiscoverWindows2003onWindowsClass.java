package loc.zenoss.testcases.ITInfrastructure.Devices.AddDevices;


import loc.zenoss.TestlinkXMLRPC;
import loc.zenoss.ZenossConstants;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import loc.zenoss.ZenossConstants;
import loc.zenoss.TestlinkXMLRPC;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class DiscoverWindows2003onWindowsClass {

private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 2045;
	private static String testCaseResult = "f"; //Fail by default
		
	@BeforeClass
	public static void setUpBeforeClass() throws Exception {
		
		sClient = new DefaultSelenium(ZenossConstants.SeleniumHubHostname, 4444,ZenossConstants.browser, ZenossConstants.testedMachine)  {
        	public void open(String url) {
        		commandProcessor.doCommand("open", new String[] {url,"true"});
        	}
        };
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
	public void AddWindows2003Devices() throws Exception {
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/
		
		sClient.open("/zport/dmd?submitted=");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(5000);
		
		sClient.click("link=IT Infrastructure");
		sClient.waitForPageToLoad("30000");
		sClient.click("//table[@id='adddevice-button']/tbody/tr[2]/td[2]/em/button[@id='ext-gen64']");
		sClient.click("//a[@id='addsingledevice-item']");//addsingledevice-item");
		Thread.sleep(5000);
		
		sClient.type("//input[@id='add-device-name']", "test-win2003-1d.zenoss.loc");
		sClient.click("//input[@id='add-device_class']");//ext-gen190");
		Thread.sleep(5000);
		sClient.click("//div[53]");//div[@id='ext-gen402']/div[53]");//div[@id='ext-gen254']/div[53]");
		sClient.click("ext-gen170");
		Thread.sleep(5000);
		sClient.click("ext-gen270");
		sClient.waitForPageToLoad("30000");
		
		SeleneseTestCase.assertFalse(sClient.isTextPresent("Traceback"));
		SeleneseTestCase.assertFalse(sClient.isTextPresent("Error"));
		
		sClient.open("link=/zport/dmd/itinfrastructure");
		Thread.sleep(5000);
		sClient.click("link=test-win2003-1d.zenoss.loc");
		sClient.waitForPageToLoad("30000");
		SeleneseTestCase.assertTrue(sClient.isElementPresent("link=/Server/Windows"));
		
		sClient.click("//ul[@id='ext-gen186']/div/li[7]/div/a/span");
		Thread.sleep(5000);
		
		sClient.type("zWinUser", "Administrator");
		sClient.type("zWinPassword", "ZenossQA1");
		sClient.click("saveZenProperties:method");
		sClient.waitForPageToLoad("30000");
		
		/* Remodel device option is still not implemented and is needed in order to execute the following steps
		 * 
		SeleneseTestCase.assertFalse(sClient.isTextPresent("Traceback"));
		SeleneseTestCase.assertFalse(sClient.isTextPresent("Error"));
		 */
		
		testCaseResult = "p";
	}
}

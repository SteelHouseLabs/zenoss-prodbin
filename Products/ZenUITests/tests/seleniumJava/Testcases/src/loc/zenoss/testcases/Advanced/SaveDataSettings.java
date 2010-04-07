package loc.zenoss.testcases.Advanced;


//import loc.zenoss.Common;
import loc.zenoss.TestlinkXMLRPC;
import loc.zenoss.ZenossConstants;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import com.thoughtworks.selenium.DefaultSelenium;
//import com.thoughtworks.selenium.SeleneseTestCase;
import com.thoughtworks.selenium.SeleneseTestCase;

public class SaveDataSettings {

	private static DefaultSelenium sClient = null;

	private static int testCaseID = 1790;
	private static String testCaseResult = "f"; //Fail by default
	private static int testPlanID = (System.getProperties().containsKey("testPlanID"))? Integer.parseInt(System.getProperties().getProperty("testPlanID")) : 2403;
	
	
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
		TestlinkXMLRPC.UpdateTestCaseResult(testCaseID, testPlanID, testCaseResult);
	}

	@Before
	public void setUp() throws Exception {
		 
	}

	@After
	public void tearDown() throws Exception {
	}
	
	
	@Test
	public void navigationSettings() throws Exception{
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/	
		 sClient.open("/zport/dmd/Dashboard");
		 sClient.waitForPageToLoad("30000");
		 sClient.click("link=Advanced");
		 sClient.waitForPageToLoad("30000");
		 Thread.sleep(3000);
		 sClient.click("link=Settings");
		 sClient.waitForPageToLoad("30000");
		 sClient.type("smtpUser", "root");
		 sClient.type("smtpPass", "meds22");
		 sClient.click("zmanage_editProperties:method");
		 sClient.waitForPageToLoad("30000");
		 Thread.sleep(3000);
		 sClient.click("link=Advanced");
		 sClient.waitForPageToLoad("30000");
		 Thread.sleep(3000);
		 sClient.click("link=Settings");
		 sClient.waitForPageToLoad("30000");
		 SeleneseTestCase.assertEquals("root", sClient.getValue("smtpUser"));	 
	}
}

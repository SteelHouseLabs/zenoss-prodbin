package loc.zenoss.testcases.Backup;


import loc.zenoss.ZenossConstants;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.TestlinkXMLRPC;
import loc.zenoss.ZenossConstants;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class BackupDefaultSettings {

	private static DefaultSelenium sClient = null;
	private SeleneseTestCase selenese = null;
	private static int testCaseID = 1790;
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
		//TestlinkXMLRPC.UpdateTestCaseResult(testCaseID, ZenossConstants.testPlanID, testCaseResult);
	}

	@Before
	public void setUp() throws Exception {
		 
	}

	@After
	public void tearDown() throws Exception {
	}
	
	@Test
	public void devicesVerified() throws Exception{
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/	
		sClient.open("/zport/dmd?submitted=");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(5000);
		sClient.open("/zport/dmd/itinfrastructure");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(8000);
     	if(sClient.isTextPresent("test-win2003-1d.zenoss.loc")){
     	 sClient.click("link=Devices");
     	 sClient.waitForPageToLoad("30000"); 
     	 sClient.click("link=Advanced");
     	 sClient.waitForPageToLoad("30000");
     	 sClient.click("link=Settings");
     	 sClient.waitForPageToLoad("30000");
     	 sClient.click("link=Backups");
     	 sClient.waitForPageToLoad("30000");
     	 sClient.click("manage_createBackup:method");
     	 sClient.waitForPageToLoad("30000");
     	 SeleneseTestCase.assertTrue(sClient.isTextPresent("Backup completed successfully")); 
     	 sClient.click("link=Devices");
     	 sClient.waitForPageToLoad("30000"); 
     	 sClient.click("link=Advanced");
     	 sClient.waitForPageToLoad("30000");
     	 sClient.click("link=Settings");
     	 sClient.waitForPageToLoad("30000");
     	 sClient.click("link=Backups");
     	 sClient.waitForPageToLoad("30000");
     	 sClient.click("fileNames:list");
     	 sClient.click("//table[@id='ext-comp-1046']/tbody/tr[2]/td[2]/em");
     	 sClient.click("manage_deleteBackups:method");
     	 sClient.waitForPageToLoad("30000");
		}else{
			sClient.open("/zport/dmd/itinfrastructure");
			sClient.waitForPageToLoad("30000");
			Thread.sleep(12000);
			sClient.click("//table[@id='adddevice-button']/tbody/tr[2]/td[2]/em/button[@id='ext-gen60']");
	     	sClient.click("ext-gen141");
	     	sClient.type("add-device-name", "test-win2003-1d.zenoss.loc");
	     	sClient.click("ext-gen206");
	     	sClient.click("//table[@id='ext-comp-1169']/tbody/tr[3]/td[2]");
			
			
		}	
	
	}

}

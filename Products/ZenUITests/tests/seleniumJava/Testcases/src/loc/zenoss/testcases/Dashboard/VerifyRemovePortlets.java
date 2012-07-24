/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2007, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.Dashboard;
import java.util.Arrays;
import java.util.List;

import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

import loc.zenoss.ZenossConstants;
import loc.zenoss.TestlinkXMLRPC;

import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;

public class VerifyRemovePortlets {	
	private static DefaultSelenium sClient = null;
	
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
		TestlinkXMLRPC.UpdateTestCaseResult(testCaseID, ZenossConstants.testPlanID, testCaseResult);
	}

	@Before
	public void setUp() throws Exception {
		 
	}

	@After
	public void tearDown() throws Exception {
	}	
	
	@Test
	public void testRestorePortlets() throws Exception{
		/*Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
		Thread.sleep(12000);*/
				
		sClient.open("http://test-cent4-64-1.zenoss.loc:8080/zport/dmd?submitted=");		
		Thread.sleep(5000);
		
		List<String> portletsNoDefault = Arrays.asList("Zenoss Issues", "Production States", "Site Window", "Root Organizers", "Messages", "Object Watch List");  

		sClient.click("link=Add portlet...");
		Thread.sleep(5000);
		
		sClient.click("yui-gen10-button");
		Thread.sleep(5000);
		
		for (String portlet : portletsNoDefault)
		{
			SeleneseTestCase.assertFalse(sClient.isTextPresent(portlet));			
		}
	}
	
	@Test
	public void testRemoveDefaultPortlets() throws Exception{		
		
		List<String> portlets = Arrays.asList("welcome_handle", "devissues_handle", "googlemaps_handle");  

		for (String portlet : portlets)
		{
			sClient.click("//div[@id='"+portlet+"']/div/div/div/div");
			Thread.sleep(1000);
			sClient.click("link=Remove Portlet");			
			Thread.sleep(5000);
			
			SeleneseTestCase.assertFalse(sClient.isElementPresent("//div[@id='"+portlet+"']"));			
		}
		testCaseResult = "p";
	}
}

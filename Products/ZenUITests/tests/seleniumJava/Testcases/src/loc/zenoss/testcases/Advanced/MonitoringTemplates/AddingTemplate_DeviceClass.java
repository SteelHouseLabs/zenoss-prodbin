/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss.testcases.Advanced.MonitoringTemplates;

import org.junit.AfterClass;
import org.junit.After;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;
import loc.zenoss.Common;
import loc.zenoss.ZenossConstants;
import com.thoughtworks.selenium.DefaultSelenium;
import com.thoughtworks.selenium.SeleneseTestCase;
import loc.zenoss.TestlinkXMLRPC;

public class AddingTemplate_DeviceClass {
	private static SeleneseTestCase selenese = null;
	private static DefaultSelenium sClient = null;
	
	private static int testCaseID = 4210;
	private static String testCaseResult = "f"; //Fail by default
		
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
		public void addingTemplate_DeviceClass() throws Exception{
			
			Common.Login(sClient, ZenossConstants.adminUserName,ZenossConstants.adminPassword);
			Thread.sleep(12000);
			
			// Set variable for Testing Template name
			String templateName = "testTemplate";
			// Open page and go to Advanced > Monitoring Templates
			sClient.open("/zport/dmd/Dashboard");
			sClient.click("link=Advanced");
			sClient.waitForPageToLoad("30000");
			sClient.click("link=Monitoring Templates");
			sClient.waitForPageToLoad("30000");
			// Click on the button "Device Class"
			sClient.click("//button[text()='Device Class']");
			// Go to device class Server/Linux
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Server']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='Server']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Linux']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='Linux']");
			Thread.sleep(2000);
			// Add new template
			sClient.click("//table[@id='footer_add_button']//button[@class=' x-btn-text add']");
			sClient.type("//input[@name='id']", templateName);
			// Click Template Path list, wait for list to populate and select "Linux in Devices/Server"
			sClient.click("//html/body/div[@id='addNewTemplateDialog']//form/div[2]/div/div/img");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[text()='Linux in Devices/Server']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[text()='Linux in Devices/Server']");
			Thread.sleep(1000);
			sClient.click("//button[text()='Submit']");
			Thread.sleep(5000);
			// Wait for templates list to refresh and show the new template
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Server']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='Server']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//div[@id='templateTree']//span[text()='Linux']")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			sClient.click("//div[@id='templateTree']//span[text()='Linux']");
			for (int second = 0;; second++) {
				if (second >= 60) break;
				try { if (sClient.isElementPresent("//span[text()='Linux']/../../../ul/li/div/a/span[contains(.,'" + templateName + "')]")) break; } catch (Exception e) {}
				Thread.sleep(1000);
			}

			// End

			Thread.sleep(1000);
			testCaseResult = "p";
		}

}

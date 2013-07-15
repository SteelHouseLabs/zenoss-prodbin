/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2007, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


package loc.zenoss;
import com.thoughtworks.selenium.DefaultSelenium;

public class Manufacturers {

	/*
	 * This method assumes that manufacturers page is already loaded
	 * Create new manufacturers
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the manufacturers was successfully added or false in other way
	 * @throws Generic Exception
	 */
	public static boolean createManufacturers(DefaultSelenium sClient, String manufacturer ) throws Exception{

		// Click on gear menu
		Thread.sleep(4000);
		sClient.click("//table[@id='ext-comp-1078']/tbody/tr[2]/td[2]/em");
		// click Add Manufacturer
		Thread.sleep(2000);
		sClient.click("//a[text()='Add Manufacturer...']");
		Thread.sleep(2000);
		sClient.type("new_id", manufacturer);
		sClient.click("//input[@id='dialog_submit']");
		Thread.sleep(8000);
		// Click on show All
		sClient.click("showAll");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(5000);

		//Verify if the manufacturer was created.
		boolean result = true;
		if(sClient.isElementPresent("//tbody[@id='Manufacturers']/tr/td/a[text()='"+manufacturer+"']")){
			result = true;
		}
		else
		{
			result = false;
			throw new Exception("The new Manufacturer was not created");
		}
		return result;
	}

	/*
	 * This method assumes that manufacturers page is already loaded
	 * and the manufacturer was created.
	 * Delete manufacturers
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the manufacturers was successfully deleted or false in other way
	 * @throws Generic Exception
	 */
	public static boolean deleteManufacturers1(DefaultSelenium sClient, String manufacturer ) throws Exception{
		// Delete Manufacturer
		// Click on the manufacturer
		sClient.click("//input[@type='checkbox' and @value='"+manufacturer+"']");
		// Click gear menu
		Thread.sleep(3000);
		sClient.click("//table[@id='ext-comp-1078']/tbody/tr[2]/td[2]/em");
		// Click Delete Manufacturers
		sClient.click("ManufacturerlistremoveManufacturers");
		Thread.sleep(2000);
		sClient.click("//input[@value='OK']");
		// Click on show All
		sClient.click("showAll");
		sClient.waitForPageToLoad("30000");
		Thread.sleep(5000);

		boolean result = false;

		if(sClient.isElementPresent("//tbody[@id='Manufacturers']/tr/td/a[text()='"+manufacturer+"']")){
			result = false;
			throw new Exception("The Manufacturer was not deleted");
		}
		else
		{
			result = true;			
		}
		return result;		
	}

	/*
	 * This method assumes that manufacturers page is already loaded
	 * and the manufacturer was created and the overview page is displayed
	 * Create Sofware manufacturers
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the new SW was successfully created or false in other way
	 * @throws Generic Exception
	 */
	public static boolean addNewSoftware(DefaultSelenium sClient, String software ) throws Exception{
		// Add SW product
		// Click gear menu
		sClient.click("//table[@id='ext-comp-1081']/tbody/tr[2]/td[2]/em");
		// Click Add Software
		Thread.sleep(2000);
		sClient.click("ProductlistaddSoftware");
		// Enter SW name
		Thread.sleep(1000);
		sClient.type("new_id", software);
		// Click Ok button
		Thread.sleep(1000);
		sClient.click("//input[@value='OK']");
		// Verify if SW is created
		Thread.sleep(4000);

		boolean result = true;
		if(sClient.isElementPresent("//tbody[@id='Products']/tr/td/a[text()='"+software+"']") && sClient.isElementPresent("//tbody[@id='Products']/tr/td[text()='Software']")){
			result = true;
		}
		else
		{
			result = false;
			throw new Exception("The new Software was not created");
		}
		return result;
	}

	/*
	 * This method assumes that manufacturers page is already loaded
	 * and the manufacturer was created and the overview page is displayed
	 * Create Hardware manufacturers
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the new HW was successfully created or false in other way
	 * @throws Generic Exception
	 */
	public static boolean addNewHarware(DefaultSelenium sClient, String hardware ) throws Exception{
		// Add HW product
		// Click gear menu
		sClient.click("//table[@id='ext-comp-1081']/tbody/tr[2]/td[2]/em");
		// Click Add Hardware
		Thread.sleep(2000);
		sClient.click("ProductlistaddHardware");
		// Enter SW name
		Thread.sleep(1000);
		sClient.type("new_id", hardware);
		// Click Ok button
		Thread.sleep(1000);
		sClient.click("//input[@value='OK']");
		// Verify if HW is created
		Thread.sleep(4000);

		boolean result = true;
		if(sClient.isElementPresent("//tbody[@id='Products']/tr/td/a[text()='"+hardware+"']") && sClient.isElementPresent("//tbody[@id='Products']/tr/td[text()='Hardware']")){
			result = true;
		}
		else
		{
			result = false;
			throw new Exception("The new Hardware was not created");
		}
		return result;
	}

	/*
	 * This method assumes that manufacturers page is already loaded
	 * and the manufacturer was created and the overview page is displayed
	 * Create OS manufacturers
	 * @author Catalina Rojas 
	 * @param sClient Selenium client connection
	 * @return Boolean true if the new OS was successfully created or false in other way
	 * @throws Generic Exception
	 */
	public static boolean addNewOS(DefaultSelenium sClient, String os ) throws Exception{
		// Add OS product
		// Click gear menu
		sClient.click("//table[@id='ext-comp-1081']/tbody/tr[2]/td[2]/em");
		// Click Add OS
		Thread.sleep(2000);
		sClient.click("ProductlistaddOS");
		// Enter OS name
		Thread.sleep(1000);
		sClient.type("new_id", os);
		// Click Ok button
		Thread.sleep(1000);
		sClient.click("//input[@value='OK']");
		// Verify OS is created
		Thread.sleep(4000);

		boolean result = true;	
		if(sClient.isElementPresent("//tbody[@id='Products']/tr/td/a[text()='"+os+"']") && sClient.isElementPresent("//tbody[@id='Products']/tr/td[text()='Operating System']") ){
			result = true;
		}
		else
		{
			result = false;
			throw new Exception("The new Operating System was not created");
		}
		return result;
	}

}
